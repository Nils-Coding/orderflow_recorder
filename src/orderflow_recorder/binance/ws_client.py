import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

import websockets
from websockets import WebSocketClientProtocol

from orderflow_recorder.config.settings import Settings
from orderflow_recorder.utils.logging import get_logger
from orderflow_recorder.storage.sinks import OrderbookSink, TradeSink


class FuturesWSClient:
	def __init__(
		self,
		settings: Settings,
		on_depth_update: Callable[[dict], Awaitable[None]],
		on_trade: Callable[[dict], Awaitable[None]],
	) -> None:
		self._settings = settings
		self._on_depth_update = on_depth_update
		self._on_trade = on_trade
		self._log = get_logger()
		self._base_url = self._settings.binance_ws_futures_base_url.rstrip("/")
		self._symbols = [s.lower() for s in self._settings.symbols_futures]
		self._depth_suffix = self._settings.futures_streams_depth
		self._trade_suffix = self._settings.futures_streams_trades

	def _build_streams_query(self) -> str:
		streams: List[str] = []
		for sym in self._symbols:
			streams.append(f"{sym}@{self._depth_suffix}")
			streams.append(f"{sym}@{self._trade_suffix}")
		return "/".join(streams)

	async def run_forever(self) -> None:
		"""
		Connect to Binance Futures combined streams and dispatch messages to callbacks.
		Auto-reconnect with exponential backoff up to 30s.
		"""
		backoff_seconds = 1
		max_backoff = 30
		streams_query = self._build_streams_query()
		uri = f"{self._base_url}?streams={streams_query}"

		self._log.info(f"Connecting to Binance Futures WS: {uri}")

		while True:
			try:
				async with websockets.connect(
					uri,
					ping_interval=20,
					ping_timeout=20,
					max_size=10 * 1024 * 1024,
				) as ws:
					backoff_seconds = 1
					await self._read_loop(ws)
			except asyncio.CancelledError:
				self._log.warning("WS client cancelled, shutting down.")
				raise
			except Exception as exc:
				self._log.error(f"WS connection error: {exc!r}")
				self._log.info(f"Reconnecting in {backoff_seconds} seconds...")
				await asyncio.sleep(backoff_seconds)
				backoff_seconds = min(backoff_seconds * 2, max_backoff)

	async def _read_loop(self, ws: WebSocketClientProtocol) -> None:
		async for msg in ws:
			try:
				payload = json.loads(msg)
			except json.JSONDecodeError:
				self._log.warning("Received non-JSON message, ignoring.")
				continue

			stream = payload.get("stream")
			data = payload.get("data")
			if not stream or not isinstance(data, dict):
				self._log.debug("Message missing 'stream' or 'data', ignoring.")
				continue

			if self._is_depth_stream(stream):
				try:
					normalized = parse_depth_message(data)
					await self._on_depth_update(normalized)
				except Exception as exc:
					self._log.error(f"Error processing depth message: {exc!r}")
			elif self._is_trade_stream(stream):
				try:
					normalized = parse_trade_message(data)
					await self._on_trade(normalized)
				except Exception as exc:
					self._log.error(f"Error processing trade message: {exc!r}")
			else:
				self._log.debug(f"Ignoring stream '{stream}' not matching depth/trade.")

	def _is_depth_stream(self, stream: str) -> bool:
		return stream.endswith(f"@{self._depth_suffix}")

	def _is_trade_stream(self, stream: str) -> bool:
		return stream.endswith(f"@{self._trade_suffix}")


def _ts_ms_to_datetime(ts_ms: Optional[int]) -> Optional[datetime]:
	if ts_ms is None:
		return None
	return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)


def parse_depth_message(raw: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Normalize Binance Futures depth update.
	Expected fields (typical):
	- E: event time (ms)
	- s: symbol
	- U: first update id
	- u: final update id
	- b: bids [[price, qty], ...]
	- a: asks [[price, qty], ...]
	"""
	event_time = _ts_ms_to_datetime(raw.get("E"))
	symbol = (raw.get("s") or "").upper()
	first_update_id = int(raw["U"]) if "U" in raw else None
	final_update_id = int(raw["u"]) if "u" in raw else None
	bids = raw.get("b") or []
	asks = raw.get("a") or []

	return {
		"source": "binance-futures",
		"type": "orderbook",
		"symbol": symbol,
		"event_time": event_time,
		"first_update_id": first_update_id,
		"final_update_id": final_update_id,
		"bids": bids,
		"asks": asks,
	}


def parse_trade_message(raw: Dict[str, Any]) -> Dict[str, Any]:
	"""
	Normalize Binance Futures aggregated trade.
	Expected fields (typical):
	- E: event time (ms)
	- T: trade time (ms)
	- a: aggregate trade id
	- s: symbol
	- p: price (string)
	- q: quantity (string)
	- m: is buyer maker (bool)
	"""
	event_time = _ts_ms_to_datetime(raw.get("E"))
	trade_time = _ts_ms_to_datetime(raw.get("T"))
	symbol = (raw.get("s") or "").upper()

	price_str = raw.get("p") or "0"
	qty_str = raw.get("q") or "0"
	price = float(price_str)
	quantity = float(qty_str)

	is_buyer_maker = bool(raw.get("m"))
	agg_trade_id = int(raw.get("a")) if raw.get("a") is not None else None

	return {
		"source": "binance-futures",
		"type": "trade",
		"symbol": symbol,
		"event_time": event_time,
		"trade_time": trade_time,
		"price": price,
		"quantity": quantity,
		"is_buyer_maker": is_buyer_maker,
		"agg_trade_id": agg_trade_id,
	}


class RecorderCallbacks:
	def __init__(self, trade_sink: TradeSink, orderbook_sink: OrderbookSink) -> None:
		self._trade_sink = trade_sink
		self._orderbook_sink = orderbook_sink

	async def on_trade(self, trade: dict) -> None:
		await self._trade_sink.write_trade(trade)

	async def on_depth_update(self, depth: dict) -> None:
		await self._orderbook_sink.write_orderbook(depth)


