import asyncio
from typing import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from orderflow_recorder.storage.models import FuturesOrderbookUpdate, FuturesTrade
from orderflow_recorder.storage.sinks import OrderbookSink, TradeSink
from orderflow_recorder.utils.logging import get_logger


class PostgresTradeSink(TradeSink):
	def __init__(self, session_factory: sessionmaker[Session]) -> None:
		self._session_factory = session_factory
		self._log = get_logger()

	async def write_trade(self, trade: dict) -> None:
		def _write() -> None:
			session = self._session_factory()
			try:
				obj = FuturesTrade(
					symbol=trade["symbol"],
					event_time=trade.get("event_time"),
					trade_time=trade.get("trade_time"),
					price=trade.get("price"),
					quantity=trade.get("quantity"),
					is_buyer_maker=trade.get("is_buyer_maker"),
					agg_trade_id=trade.get("agg_trade_id"),
				)
				session.add(obj)
				session.commit()
			except SQLAlchemyError as exc:
				session.rollback()
				raise exc
			finally:
				session.close()

		try:
			await asyncio.to_thread(_write)
		except Exception as exc:
			self._log.error(f"PostgresTradeSink.write_trade failed: {exc!r}")


class PostgresOrderbookSink(OrderbookSink):
	def __init__(self, session_factory: sessionmaker[Session]) -> None:
		self._session_factory = session_factory
		self._log = get_logger()

	async def write_orderbook(self, depth: dict) -> None:
		def _write() -> None:
			session = self._session_factory()
			try:
				obj = FuturesOrderbookUpdate(
					symbol=depth["symbol"],
					event_time=depth.get("event_time"),
					first_update_id=depth.get("first_update_id"),
					final_update_id=depth.get("final_update_id"),
					bids=depth.get("bids") or [],
					asks=depth.get("asks") or [],
				)
				session.add(obj)
				session.commit()
			except SQLAlchemyError as exc:
				session.rollback()
				raise exc
			finally:
				session.close()

		try:
			await asyncio.to_thread(_write)
		except Exception as exc:
			self._log.error(f"PostgresOrderbookSink.write_orderbook failed: {exc!r}")


