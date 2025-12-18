# API Usage Guide

This document describes how to consume the **Orderflow Data API** from the Frontend Application (or any other client).

## 1. Connection Details

*   **Base URL (Production):** `https://orderflow-api-185074207738.europe-west1.run.app/api/v1`
*   **Local URL (Dev):** `http://localhost:8000/api/v1` (if running locally via `uvicorn`)

### Authentication
The API is protected by a simple API Key.
You must include the following header in **every request**:

```http
X-API-Key: YOUR_SECRET_KEY
```

*(Note: In the Frontend project, store this key in `.env` as `PUBLIC_API_KEY` or similar).*

---

## 2. Endpoints

### GET /candles
Fetches aggregated candle data for a specific day.

**Parameters:**
| Param | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `symbol` | string | The crypto asset pair | `btcusdt`, `ethusdt` |
| `date` | string | Date in YYYY-MM-DD format | `2025-12-11` |
| `resolution` | string | Timeframe (`1s` or `1m`) | `1m` |

**Example Request:**
```http
GET /candles?symbol=btcusdt&date=2025-12-11&resolution=1m
```

### Response Format (JSON)

```json
{
  "symbol": "BTCUSDT",
  "date": "2025-12-11",
  "resolution": "1m",
  "count": 1440,
  "data": [
    {
      "time": 1702252800,      // Unix Timestamp (Seconds)
      "open": 42000.50,
      "high": 42100.00,
      "low": 41950.00,
      "close": 42050.00,
      "vol_total": 150.5,      // Total Volume (BTC)
      "vol_buy": 80.2,         // Buyer Aggressor Volume
      "vol_sell": 70.3,        // Seller Aggressor Volume
      "vol_delta": 9.9,        // Net Buying Pressure (Buy - Sell)
      "trade_count": 550       // Number of trades
    },
    ...
  ]
}
```

---

## 3. Usage in TypeScript / Vue

Here is a helper function to fetch data cleanly.

```typescript
// types.ts
export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  vol_total: number;
  vol_delta: number;
}

// api.ts
const API_URL = import.meta.env.PUBLIC_API_URL;
const API_KEY = import.meta.env.PUBLIC_API_KEY;

export async function fetchCandles(symbol: string, date: string): Promise<Candle[]> {
  const url = `${API_URL}/candles?symbol=${symbol}&date=${date}&resolution=1m`;
  
  const response = await fetch(url, {
    headers: {
      'X-API-Key': API_KEY
    }
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }

  const json = await response.json();
  return json.data;
}
```

