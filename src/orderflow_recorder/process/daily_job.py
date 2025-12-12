import asyncio
import io
import json
import logging
import os
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

import pandas as pd
from google.cloud import storage

from orderflow_recorder.config.settings import get_settings

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("daily_processor")

def get_gcs_client():
    # Helper to get client with credentials if local
    key_path = Path("gcp-key.json")
    if key_path.exists() and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path.absolute())
    return storage.Client()

def parse_blob_date(blob_name: str) -> datetime:
    # Expected format: raw/SYMBOL/YYYY-MM-DD/HH-MM-SS_type.csv
    try:
        parts = blob_name.split("/")
        date_str = parts[2] # YYYY-MM-DD
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return None

def process_symbol_day(bucket_name: str, symbol: str, target_date: datetime):
    """
    Process one day of data for one symbol.
    """
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    
    date_str = target_date.strftime("%Y-%m-%d")
    prefix = f"raw/{symbol}/{date_str}/"
    
    log.info(f"Checking for data: {prefix}")
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    if not blobs:
        log.warning(f"No data found for {symbol} on {date_str}. Skipping.")
        return

    log.info(f"Found {len(blobs)} chunks. Downloading...")

    trades_list = []
    
    # We won't process Orderbook snapshots fully in this V1 as per concept (focus on Trades first for OHLC/Delta).
    # Reconstructing full book from snapshots for 'Avg Spread' requires complex logic (merging snapshots).
    # For now, we aggregate TRADES. 
    # TODO: Add Depth aggregation logic if depth files are needed for 'Avg Spread'.
    
    # Download and parse Trades
    trade_blobs = [b for b in blobs if "_trades.csv" in b.name]
    
    for blob in trade_blobs:
        content = blob.download_as_text()
        if not content.strip():
            continue
        try:
            df_chunk = pd.read_csv(io.StringIO(content))
            trades_list.append(df_chunk)
        except Exception as e:
            log.error(f"Failed to parse {blob.name}: {e}")

    if not trades_list:
        log.warning("No valid trade rows found.")
        return

    # Combine
    df = pd.concat(trades_list, ignore_index=True)
    
    # Pre-processing
    # Use 'mixed' format to handle potential variations (e.g. with/without microseconds)
    df['timestamp'] = pd.to_datetime(df['event_time'], format='mixed') # event_time is the source of truth
    df.set_index('timestamp', inplace=True)
    df.sort_index(inplace=True)
    
    # Strict Date Filtering (UTC 00:00:00 to 23:59:59)
    # Ensure we only keep data for the actual target_date, removing overlap from buffer
    start_ts = pd.Timestamp(target_date).replace(hour=0, minute=0, second=0, microsecond=0)
    end_ts = start_ts + pd.Timedelta(days=1)
    df = df[(df.index >= start_ts) & (df.index < end_ts)]
    
    if df.empty:
        log.warning(f"No data left after date filtering for {date_str}.")
        return

    # Calculate side volumes
    # is_buyer_maker = True -> Seller Aggressor (Sell Vol)
    # is_buyer_maker = False -> Buyer Aggressor (Buy Vol)
    df['vol_buy'] = df.apply(lambda x: x['quantity'] if not x['is_buyer_maker'] else 0, axis=1)
    df['vol_sell'] = df.apply(lambda x: x['quantity'] if x['is_buyer_maker'] else 0, axis=1)

    # Aggregation Logic
    # 1s Resolution
    ohlc_dict = {
        'price': ['first', 'max', 'min', 'last'],
        'quantity': 'sum',
        'vol_buy': 'sum',
        'vol_sell': 'sum',
        'source': 'count' # Just to count trades
    }
    
    df_1s = df.resample('1s').agg(ohlc_dict)
    
    # Rename columns
    df_1s.columns = ['open', 'high', 'low', 'close', 'vol_total', 'vol_buy', 'vol_sell', 'trade_count']
    
    # Calculate Delta
    df_1s['vol_delta'] = df_1s['vol_buy'] - df_1s['vol_sell']
    
    # Forward fill Prices (if no trade, price stays same)
    df_1s['close'] = df_1s['close'].ffill()
    df_1s['open'] = df_1s['open'].fillna(df_1s['close'])
    df_1s['high'] = df_1s['high'].fillna(df_1s['close'])
    df_1s['low'] = df_1s['low'].fillna(df_1s['close'])
    
    # Zero fill Volumes (if no trade, vol is 0)
    vol_cols = ['vol_total', 'vol_buy', 'vol_sell', 'vol_delta', 'trade_count']
    df_1s[vol_cols] = df_1s[vol_cols].fillna(0)
    
    # Round volumes to 6 decimal places to save space but keep precision
    df_1s = df_1s.round({
        'vol_total': 6, 'vol_buy': 6, 'vol_sell': 6, 'vol_delta': 6,
        'open': 2, 'high': 2, 'low': 2, 'close': 2  # Prices usually 2 decimals for USDT pairs (or more for others)
    })

    # 1m Resolution (Resample from 1s to be accurate)
    df_1m = df_1s.resample('1min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'vol_total': 'sum',
        'vol_buy': 'sum',
        'vol_sell': 'sum',
        'vol_delta': 'sum',
        'trade_count': 'sum'
    })
    
    # Upload Aggregated Files
    upload_df(bucket, df_1s, f"aggregated/{symbol}/{date_str}_1s.csv")
    upload_df(bucket, df_1m, f"aggregated/{symbol}/{date_str}_1m.csv")
    
    log.info(f"Aggregation complete. 1s: {len(df_1s)} rows, 1m: {len(df_1m)} rows.")

    # Archiving (Zip Raw Files)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for blob in blobs:
            # Name inside zip: HH-MM-SS_type.csv
            file_name = blob.name.split("/")[-1] 
            zip_file.writestr(file_name, blob.download_as_bytes())
    
    zip_blob_name = f"archive/{symbol}/{date_str}_raw.zip"
    zip_blob = bucket.blob(zip_blob_name)
    zip_blob.upload_from_file(zip_buffer, content_type="application/zip", rewind=True)
    log.info(f"Archived raw files to {zip_blob_name}")

    # Delete Raw Files
    # Safety check: Ensure Zip exists before deleting?
    if zip_blob.exists():
        batch = client.batch()
        for blob in blobs:
            blob.delete()
        log.info(f"Deleted {len(blobs)} raw files.")
    else:
        log.error("Archive upload failed? Skipping deletion for safety.")


def upload_df(bucket, df: pd.DataFrame, path: str):
    blob = bucket.blob(path)
    blob.upload_from_string(df.to_csv(), content_type="text/csv")
    log.info(f"Uploaded {path}")


def main():
    settings = get_settings()
    bucket_name = settings.gcs_bucket_name
    symbols = settings.symbols_futures
    
    # Default: Process Yesterday
    # If run at 01:00 UTC on 20th, we process 19th.
    target_date = datetime.now(timezone.utc) - timedelta(days=1)
    
    # Allow manual override via env var for testing (DATE=2024-05-20)
    if os.environ.get("FORCE_DATE"):
        target_date = datetime.strptime(os.environ["FORCE_DATE"], "%Y-%m-%d").replace(tzinfo=timezone.utc)

    log.info(f"Starting Daily Job for {target_date.strftime('%Y-%m-%d')}")
    log.info(f"Symbols: {symbols}")

    for symbol in symbols:
        try:
            process_symbol_day(bucket_name, symbol.upper(), target_date)
        except Exception as e:
            log.error(f"Error processing {symbol}: {e}", exc_info=True)

    log.info("Job Finished.")

if __name__ == "__main__":
    main()

