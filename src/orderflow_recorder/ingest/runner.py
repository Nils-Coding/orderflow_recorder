import asyncio

from orderflow_recorder.config.settings import get_settings
from orderflow_recorder.storage.db import get_engine, get_session_factory
from orderflow_recorder.storage.postgres_sinks import PostgresOrderbookSink, PostgresTradeSink
from orderflow_recorder.binance.ws_client import FuturesWSClient, RecorderCallbacks
from orderflow_recorder.utils.logging import setup_logging, get_logger


async def run() -> None:
	setup_logging()
	log = get_logger()
	settings = get_settings()

	log.info("Starting ingest runner")

	engine = get_engine(settings)
	SessionLocal = get_session_factory(engine)

	trade_sink = PostgresTradeSink(SessionLocal)
	orderbook_sink = PostgresOrderbookSink(SessionLocal)

	callbacks = RecorderCallbacks(trade_sink, orderbook_sink)
	client = FuturesWSClient(settings, callbacks.on_depth_update, callbacks.on_trade)

	await client.run_forever()


def main() -> None:
	asyncio.run(run())


