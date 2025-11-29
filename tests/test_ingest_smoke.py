import os
import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select, func

from orderflow_recorder.config.settings import get_settings
from orderflow_recorder.storage.db import get_engine, get_session_factory, init_db
from orderflow_recorder.storage.models import FuturesOrderbookUpdate, FuturesTrade
from orderflow_recorder.ingest.runner import run as ingest_run
from orderflow_recorder.utils.logging import setup_logging


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not os.getenv("RUN_INGEST_SMOKE"), reason="integration smoke test disabled")
async def test_ingest_smoke_inserts_data():
	# Arrange DB
	setup_logging("INFO")
	settings = get_settings()
	engine = get_engine(settings)
	init_db(engine)
	SessionLocal = get_session_factory(engine)

	# Run ingest for a short period, then cancel
	task = asyncio.create_task(ingest_run())
	try:
		await asyncio.sleep(20)  # let it ingest some data
	finally:
		task.cancel()
		with pytest.raises(asyncio.CancelledError):
			await task

	# Assert rows inserted
	with SessionLocal() as session:
		trades_count = session.execute(select(func.count()).select_from(FuturesTrade)).scalar_one()
		orderbook_count = session.execute(select(func.count()).select_from(FuturesOrderbookUpdate)).scalar_one()
		assert trades_count > 0 or orderbook_count > 0


