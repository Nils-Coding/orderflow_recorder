import asyncio
import csv
import io
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any

from google.cloud import storage
from orderflow_recorder.config.settings import Settings
from orderflow_recorder.storage.sinks import OrderbookSink, TradeSink
from orderflow_recorder.utils.logging import get_logger


class GcsCsvSink(TradeSink, OrderbookSink):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._log = get_logger()
        self._bucket_name = settings.gcs_bucket_name
        self._buffer_seconds = settings.buffer_seconds

        # Buffers: symbol -> list of dicts
        self._trade_buffer: Dict[str, List[Dict[str, Any]]] = {}
        self._depth_buffer: Dict[str, List[Dict[str, Any]]] = {}
        
        self._lock = asyncio.Lock()
        self._running = False
        self._bg_task = None

        # Initialize GCS Client
        # GOOGLE_APPLICATION_CREDENTIALS should be set in env
        try:
            self._client = storage.Client()
            self._bucket = self._client.bucket(self._bucket_name)
            self._log.info(f"Initialized GCS Sink for bucket: {self._bucket_name}")
        except Exception as e:
            self._log.error(f"Failed to initialize GCS client: {e}")
            self._client = None
            self._bucket = None

    async def start(self) -> None:
        """Start the periodic flush loop."""
        self._running = True
        self._bg_task = asyncio.create_task(self._flush_loop())
        self._log.info(f"GCS Sink started. Buffer flush every {self._buffer_seconds}s.")

    async def stop(self) -> None:
        """Stop the loop and flush remaining data."""
        self._running = False
        if self._bg_task:
            self._bg_task.cancel()
            try:
                await self._bg_task
            except asyncio.CancelledError:
                pass
        await self._flush()
        self._log.info("GCS Sink stopped.")

    async def write_trade(self, trade: dict) -> None:
        symbol = trade["symbol"]
        async with self._lock:
            if symbol not in self._trade_buffer:
                self._trade_buffer[symbol] = []
            self._trade_buffer[symbol].append(trade)

    async def write_orderbook(self, depth: dict) -> None:
        symbol = depth["symbol"]
        async with self._lock:
            if symbol not in self._depth_buffer:
                self._depth_buffer[symbol] = []
            self._depth_buffer[symbol].append(depth)

    async def _flush_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._buffer_seconds)
            try:
                await self._flush()
            except Exception as exc:
                self._log.error(f"Error flushing to GCS: {exc!r}")

    async def _flush(self) -> None:
        async with self._lock:
            if not self._trade_buffer and not self._depth_buffer:
                return
            
            # Swap buffers
            trades_snapshot = self._trade_buffer
            depth_snapshot = self._depth_buffer
            self._trade_buffer = {}
            self._depth_buffer = {}

        if not self._client:
            self._log.warning("No GCS client available, skipping upload (data lost).")
            return

        # Upload in thread to avoid blocking event loop
        await asyncio.to_thread(self._upload_batch, trades_snapshot, depth_snapshot)

    def _upload_batch(self, trades_map: Dict[str, List[dict]], depth_map: Dict[str, List[dict]]) -> None:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")

        # Upload trades
        for symbol, trades in trades_map.items():
            if not trades:
                continue
            
            # CSV content
            output = io.StringIO()
            # Define CSV headers based on keys of the first element, or fixed schema
            # Fixed schema is safer:
            fieldnames = [
                "source", "type", "symbol", "event_time", "trade_time", 
                "price", "quantity", "is_buyer_maker", "agg_trade_id"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            # writer.writeheader() # Maybe no header for raw chunks to save space? 
            # Or yes header? Standard CSVs usually have headers. 
            # The user wants to aggregate later. Headers make it safer for pandas.
            writer.writeheader()
            writer.writerows(trades)
            
            blob_name = f"raw/{symbol}/{date_str}/{time_str}_trades.csv"
            self._upload_string_content(output.getvalue(), blob_name)

        # Upload depth
        for symbol, updates in depth_map.items():
            if not updates:
                continue

            output = io.StringIO()
            fieldnames = [
                "source", "type", "symbol", "event_time", 
                "first_update_id", "final_update_id", "bids", "asks"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            # Need to JSON-serialize bids/asks lists for CSV
            for row in updates:
                row_copy = row.copy()
                row_copy["bids"] = json.dumps(row_copy["bids"])
                row_copy["asks"] = json.dumps(row_copy["asks"])
                writer.writerow(row_copy)
            
            blob_name = f"raw/{symbol}/{date_str}/{time_str}_depth.csv"
            self._upload_string_content(output.getvalue(), blob_name)

    def _upload_string_content(self, content: str, blob_name: str) -> None:
        try:
            blob = self._bucket.blob(blob_name)
            blob.upload_from_string(content, content_type="text/csv")
            self._log.debug(f"Uploaded {blob_name}")
        except Exception as e:
            self._log.error(f"Failed to upload {blob_name}: {e}")


