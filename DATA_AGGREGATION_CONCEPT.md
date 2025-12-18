# Data Aggregation & Analytics Concept

## 1. Overview
This document defines the strategy for processing raw high-frequency cryptocurrency market data (Binance Futures) into analytical time-series datasets. The goal is to transform raw tick-by-tick data into structured features suitable for financial analysis, quantitative research, and Machine Learning models.

**Architecture:**
1.  **Ingest:** Raw trades and orderbook updates are buffered and uploaded to Google Cloud Storage (GCS) in 1-minute CSV chunks.
2.  **Process:** A daily Cloud Run Job aggregates these chunks.
3.  **Output:** Clean, single-file CSVs per day/symbol (at 1s and 1m resolution) are stored in GCS for team consumption.

**Changelog:**
*   **2025-12-16 14:46 UTC:** Switched from `depth5@100ms` to **`depth20@100ms`**. This provides deeper visibility into liquidity walls and spoofing attempts (Top 20 levels instead of Top 5).

---

## 2. Financial Analytics View (The "Why")

We combine **Trades** (Aggression/Action) with **Orderbook Snapshots** (Liquidity/Intent) to find predictive patterns.

### A. Orderflow Signals (Trades)
Who is aggressive? Who is paying the spread?

| Metric | Definition | Financial Interpretation |
| :--- | :--- | :--- |
| **Volume_Delta** | `Vol_Buy - Vol_Sell` | **Net Aggressor Pressure.** Divergence between Price (Higher High) and Delta (Lower High) often signals a reversal (Absorption). |
| **CVD** | Cumulative Volume Delta | Intraday trend of aggression. |
| **Trade_Count** | Number of executions | High Vol + Low Count = Whales. High Vol + High Count = Retail FOMO. |

### B. Liquidity Signals (Orderbook Snapshots)
The "Stroboscope" View: We see the state of the book every 100ms. We do not reconstruct the full matching engine, but compare snapshots to detect intent.

| Pattern | Definition | Interpretation |
| :--- | :--- | :--- |
| **Absorption** | Trades indicate heavy SELLING, but Price stays stable at a Support level. | A passive Buyer (Iceberg) is absorbing the selling pressure. **Bullish Reversal.** |
| **Exhaustion** | Trades indicate heavy BUYING, Orderbook Ask is thin, but Price stops rising. | Buyers are running out of steam or hitting hidden walls. **Bearish Reversal.** |
| **Liquidity Vacuum** | Ask-Side liquidity suddenly vanishes (Spoofers pull orders). | Path of least resistance is up. Volatility is likely to spike. |
| **Imbalance** | Ratio of Bid Qty vs Ask Qty (e.g. at Top 20 levels). | Predictive for short-term direction pressure. |

---

## 3. Technical Implementation

### Data Source (Raw)
*   **Trades:** `timestamp, price, quantity, is_buyer_maker`
*   **Depth (Snapshots):** `timestamp, bids (json), asks (json)`
    *   Since we use `depth20@100ms` (Partial Depth Streams), we handle these as independent snapshots. We do NOT maintain a local orderbook via delta-updates, as we lack the intermediate events. Instead, we perform **Snapshot Comparison** (e.g., did a wall disappear between T1 and T2?).

### Output Schema (Aggregated CSV)
Files will be named: `aggregated/{SYMBOL}/{YYYY-MM-DD}_{RESOLUTION}.csv` (e.g., `2025-12-11_1s.csv`).

**Columns:**
1.  `timestamp` (UTC, ISO8601)
2.  `open, high, low, close`
3.  `vwap`
4.  `vol_total, vol_buy, vol_sell, vol_delta`
5.  `trade_count`
6.  `avg_spread` (Mean of ask[0] - bid[0])
7.  `imbalance_l20` (Optional future feature: BidQty / (BidQty + AskQty))

### Handling Gaps
*   **Price (OHLC):** Forward Fill.
*   **Volume/Counts:** Zero Fill.

---

## 4. AI & ML Strategy (Outlook)
For predictive modeling, we will treat this as a Time-Series Classification problem ("Will price go UP or DOWN in next 5 mins?").

*   **Approach:** Instead of Large Language Models (LLMs), we will focus on:
    1.  **Gradient Boosting (XGBoost/LightGBM):** Strong baseline for tabular features (Delta, Imbalance).
    2.  **Time-Series Foundation Models (Chronos/Moirai):** New transformer-based models specifically for numerical time-series.
*   **Role of LLMs:** Used as "Analysts" to generate textual reports describing the detected patterns ("Detected Divergence at 14:00 UTC"), but not for the raw number crunching.
