from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi import FastAPI
from pydantic import BaseModel

from orderflow_recorder.config.settings import get_settings, Settings
from orderflow_api.service import get_candle_data

app = FastAPI(title="Orderflow Data API", version="0.1.0")

# --- Security ---
async def verify_api_key(
    x_api_key: str = Header(..., description="Your secret API Key"),
    settings: Settings = Depends(get_settings)
):
    """
    Validates the X-API-Key header against the one in settings.
    """
    # If no API key is configured in env, we might default to insecure or block all.
    # Here we block if env var is missing or mismatch.
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Server misconfiguration: API_KEY not set."
        )
        
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return x_api_key

# --- Models ---
class Candle(BaseModel):
    time: int  # Unix timestamp
    open: float
    high: float
    low: float
    close: float
    vol_total: float
    vol_buy: float
    vol_sell: float
    vol_delta: float
    trade_count: int

class CandleResponse(BaseModel):
    symbol: str
    date: str
    resolution: str
    count: int
    data: List[Candle]

# --- Routes ---
router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])

@router.get("/candles", response_model=CandleResponse)
async def get_candles(
    symbol: str, 
    date: str, 
    resolution: str = "1m",
    settings: Settings = Depends(get_settings)
):
    """
    Fetch aggregated candle data for a specific day.
    
    - **symbol**: e.g. 'btcusdt'
    - **date**: Format 'YYYY-MM-DD'
    - **resolution**: '1m' or '1s'
    """
    # Validate resolution
    if resolution not in ["1m", "1s"]:
        raise HTTPException(status_code=400, detail="Resolution must be '1m' or '1s'")

    try:
        data = await get_candle_data(
            bucket_name=settings.gcs_bucket_name,
            symbol=symbol.upper(),
            date_str=date,
            resolution=resolution
        )
        
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol} on {date}")
            
        return CandleResponse(
            symbol=symbol.upper(),
            date=date,
            resolution=resolution,
            count=len(data),
            data=data
        )
    except Exception as e:
        # Log error here in real app
        print(f"Error fetching data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "ok"}

