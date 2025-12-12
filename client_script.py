import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000/api/v1/candles")
#API_KEY = os.environ.get("API_KEY")
API_KEY = "orderflow123go"
SYMBOL = "btcusdt"
DATE = "2025-12-11"
RESOLUTION = "1m"

if not API_KEY:
    raise ValueError("API_KEY not found in .env file or environment variables")

def fetch_data():
    print(f"Fetching data from {API_URL}...")
    headers = {"X-API-Key": API_KEY}
    params = {
        "symbol": SYMBOL,
        "date": DATE,
        "resolution": RESOLUTION
    }
    
    try:
        resp = requests.get(API_URL, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        print(f"Success! Received {data['count']} candles.")
        return data['data']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return []

def plot_orderflow(candles):
    if not candles:
        return

    df = pd.DataFrame(candles)
    # Convert unix seconds back to datetime for Plotly
    df['date'] = pd.to_datetime(df['time'], unit='s')
    
    # Create Subplots: Row 1 = Price, Row 2 = Volume Delta
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=(f"{SYMBOL.upper()} Price ({RESOLUTION})", "Volume Delta")
    )

    # 1. Candlestick Chart
    fig.add_trace(go.Candlestick(
        x=df['date'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name='Price'
    ), row=1, col=1)

    # 2. Volume Delta (Color coded)
    # Green for positive delta, Red for negative
    colors = ['green' if x >= 0 else 'red' for x in df['vol_delta']]
    
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['vol_delta'],
        name='Delta',
        marker_color=colors
    ), row=2, col=1)

    # Layout
    fig.update_layout(
        title=f"Orderflow Analysis: {SYMBOL.upper()} - {DATE}",
        xaxis_rangeslider_visible=False,
        height=800,
        template="plotly_dark"
    )

    fig.show()

if __name__ == "__main__":
    candles = fetch_data()
    plot_orderflow(candles)
