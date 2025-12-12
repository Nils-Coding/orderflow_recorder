import asyncio
import io
import pandas as pd
from typing import List, Dict, Any
from google.cloud import storage
import os
from pathlib import Path

# Cache GCS client to reuse connection pool
_gcs_client = None

def get_gcs_client():
    global _gcs_client
    if _gcs_client is None:
        # Helper to get client with credentials if local
        key_path = Path("gcp-key.json")
        if key_path.exists() and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path.absolute())
        _gcs_client = storage.Client()
    return _gcs_client

async def get_candle_data(bucket_name: str, symbol: str, date_str: str, resolution: str) -> List[Dict[str, Any]]:
    """
    Downloads the CSV from GCS and converts it to a list of dicts for the API response.
    Non-blocking (runs in thread pool).
    """
    return await asyncio.to_thread(_fetch_and_parse, bucket_name, symbol, date_str, resolution)

def _fetch_and_parse(bucket_name: str, symbol: str, date_str: str, resolution: str) -> List[Dict[str, Any]]:
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    
    # Path format: aggregated/BTCUSDT/2024-12-11_1m.csv
    blob_path = f"aggregated/{symbol}/{date_str}_{resolution}.csv"
    blob = bucket.blob(blob_path)
    
    if not blob.exists():
        return []
        
    content = blob.download_as_text()
    if not content.strip():
        return []

    # Parse with Pandas
    df = pd.read_csv(io.StringIO(content))
    
    # Transform to API format (list of dicts)
    # 1. Convert timestamp to Unix int (seconds) or millis
    # TradingView charts usually like Unix seconds
    df['time'] = pd.to_datetime(df['timestamp']).astype(int) // 10**9
    
    # Select columns we want
    cols = [
        'time', 'open', 'high', 'low', 'close', 
        'vol_total', 'vol_buy', 'vol_sell', 'vol_delta', 'trade_count'
    ]
    
    # Ensure all columns exist (in case CSV schema drifts)
    # If missing, fill with 0
    for col in cols:
        if col not in df.columns:
            df[col] = 0
            
    # Convert to list of dicts
    records = df[cols].to_dict(orient='records')
    return records

