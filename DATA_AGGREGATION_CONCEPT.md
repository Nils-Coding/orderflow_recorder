# Data Aggregation & Analytics Concept

## 1. Overview
This document defines the strategy for processing raw high-frequency cryptocurrency market data (Binance Futures) into analytical time-series datasets. The goal is to transform raw tick-by-tick data into structured features suitable for financial analysis, quantitative research, and Machine Learning models.

**Architecture:**
1.  **Ingest:** Raw trades and orderbook updates are buffered and uploaded to Google Cloud Storage (GCS) in 1-minute CSV chunks.
2.  **Process:** A daily Cloud Run Job aggregates these chunks.
3.  **Output:** Clean, single-file CSVs per day/symbol (at 1s and 1m resolution) are stored in GCS for team consumption.

---

## 2. Financial Analytics View
We go beyond standard OHLC (Open, High, Low, Close) candles. The focus is on **Orderflow**, which analyzes the aggressive buying/selling pressure (Trades) against the passive liquidity (Orderbook).

### A. Price & Volume (The "What")
Standard market data metrics.

| Metric | Definition | Financial Interpretation |
| :--- | :--- | :--- |
| **OHLC** | Open, High, Low, Close Price | Standard price action. |
| **VWAP** | Volume Weighted Average Price | The "fair" price of the interval. Institutional benchmark. Price > VWAP implies bullish intraday sentiment. |
| **Volume_Total** | Total quantity traded (in Base Asset, e.g., BTC) | Activity level. High volume validates price moves; low volume suggests lack of conviction. |
| **Trade_Count** | Number of individual executions | **Whale vs. Retail detection.** <br>High Volume + Low Trade Count = Large Players active.<br>High Volume + High Trade Count = HFT/Retail herd. |

### B. Orderflow & Delta (The "Why")
Analyzing who initiated the trade (Aggressor).
*   **Buyer Aggressor:** Trader placed a MARKET BUY order (taking liquidity from Ask).
*   **Seller Aggressor:** Trader placed a MARKET SELL order (taking liquidity from Bid).

| Metric | Definition | Financial Interpretation |
| :--- | :--- | :--- |
| **Volume_Buy** | Volume where aggressor was Buyer | Buying pressure. |
| **Volume_Sell** | Volume where aggressor was Seller | Selling pressure. |
| **Volume_Delta** | `Volume_Buy - Volume_Sell` | **Net Aggressor Pressure.**<br>**Divergence:** If Price makes a New High but Delta makes a Lower High, the move is running out of steam (Absorption). |
| **CVD** | Cumulative Volume Delta (Intraday) | Running total of Delta since 00:00 UTC. Shows the trend of aggression throughout the day. |

### C. Liquidity & Orderbook (The "Resistance")
Analyzing the passive limit orders resting in the book.

| Metric | Definition | Financial Interpretation |
| :--- | :--- | :--- |
| **Avg_Spread** | Average `(BestAsk - BestBid)` | **Cost of Liquidity.** Spreads widen during volatility or uncertainty. Tight spreads indicate healthy liquidity. |
| **L1_Imbalance** | `BidQty / (BidQty + AskQty)` (at Best Price) | **Orderbook Pressure.** <br>> 0.5: More support (Bids) than resistance (Asks).<br>< 0.5: More resistance than support.<br>*Note: Limit orders can be pulled (spoofing), so this is less reliable than Trade Delta.* |

---

## 3. Technical Implementation

### Data Source (Raw)
*   **Trades:** `timestamp, price, quantity, is_buyer_maker`
    *   *Note on `is_buyer_maker`:* If `True`, the maker was the buyer -> Aggressor was Seller. If `False`, Aggressor was Buyer.
*   **Depth:** `timestamp, bids (json), asks (json)` (Snapshots)

### Output Schema (Aggregated CSV)
Files will be named: `aggregated/{SYMBOL}/{YYYY-MM-DD}_{RESOLUTION}.csv` (e.g., `2024-05-20_1s.csv`).

**Columns:**
1.  `timestamp` (UTC, ISO8601)
2.  `open`
3.  `high`
4.  `low`
5.  `close`
6.  `vwap`
7.  `vol_total` (Sum of qty)
8.  `vol_buy` (Sum of qty where is_buyer_maker=False)
9.  `vol_sell` (Sum of qty where is_buyer_maker=True)
10. `vol_delta` (vol_buy - vol_sell)
11. `trade_count` (Count of rows)
12. `avg_spread` (Mean of ask[0] - bid[0])
13. `avg_bid_qty` (Mean of bid[0] qty)
14. `avg_ask_qty` (Mean of ask[0] qty)

### Handling Gaps
*   **Price (OHLC):** Forward Fill. If no trades occur in a second, Close of T-1 becomes Open/High/Low/Close of T.
*   **Volume/Counts:** Zero Fill. If no trades, Volume is 0.

### Tech Stack
*   **Language:** Python
*   **Engine:** Pandas (processing in-memory is sufficient for daily chunks).
*   **Storage:** Google Cloud Storage.

---

## 4. Workflow for Team
1.  **Daily Job** runs at 01:00 UTC.
2.  It processes the previous day (00:00-23:59).
3.  It uploads `aggregated/BTCUSDT/YYYY-MM-DD_1s.csv`.
4.  **Analysts** download these specific files for research (Python/Jupyter/Excel).
5.  **Archive:** Raw files are zipped to `archive/BTCUSDT/YYYY-MM-DD_raw.zip` to reduce costs.

