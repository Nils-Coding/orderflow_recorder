from typing import Protocol


class TradeSink(Protocol):
	async def write_trade(self, trade: dict) -> None: ...


class OrderbookSink(Protocol):
	async def write_orderbook(self, depth: dict) -> None: ...


