import asyncio
import os
from pathlib import Path

from aiohttp import web
from orderflow_recorder.config.settings import get_settings
from orderflow_recorder.storage.gcs_sinks import GcsCsvSink
from orderflow_recorder.binance.ws_client import FuturesWSClient, RecorderCallbacks
from orderflow_recorder.utils.logging import setup_logging, get_logger


async def health_check(request):
    return web.Response(text="OK")

async def start_dummy_server(port: int = 8080):
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def run() -> None:
    setup_logging()
    log = get_logger()
    settings = get_settings()

    log.info("Starting ingest runner (GCS Mode)")
    
    # Ensure google credentials are set if provided locally
    key_path = Path("gcp-key.json")
    if key_path.exists() and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path.absolute())
        log.info(f"Loaded credentials from {key_path}")

    # Start dummy server for Cloud Run health checks
    port = int(os.environ.get("PORT", 8080))
    log.info(f"Starting dummy health check server on port {port}")
    await start_dummy_server(port)

    sink = GcsCsvSink(settings)
    await sink.start()

    callbacks = RecorderCallbacks(sink, sink)
    client = FuturesWSClient(settings, callbacks.on_depth_update, callbacks.on_trade)

    try:
        await client.run_forever()
    finally:
        await sink.stop()


def main() -> None:
    asyncio.run(run())
