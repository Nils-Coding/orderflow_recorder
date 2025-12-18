# Analysis Roadmap: Orderflow Quantitative Research

This document outlines the strategy for analyzing collected orderflow data to find predictive signals for crypto assets (BTC, ETH).

## Phase 1: Mengengerüst & Statistik (`volatility_report.py`)
Goal: Understand the frequency and magnitude of market moves to define what constitutes an "Event".

### Konzept
We calculate returns over fixed rolling windows (e.g., 5 min, 15 min). We group these returns into buckets to see distribution.

**Separation:** We explicitly distinguish between **Pumps** (Positive Returns) and **Crashes/Dumps** (Negative Returns), as market mechanics differ (Greed vs. Fear/Liquidation).

### Implementation Plan
1.  Load data (e.g., last 7 days).
2.  Calculate `rolling_return = (close / close.shift(N)) - 1`.
3.  Filter for moves > Threshold (e.g., start at 0.5%).
4.  **Bucketing:**
    *   `0.5% - 0.6%`: 12 Events
    *   `0.6% - 0.7%`: 8 Events
    *   `...`
    *   `> 2.0%`: 1 Event
5.  **Output:** A clear table/histogram for Pumps and Dumps separately.

---

## Phase 2: Pattern Discovery (Explorative)
Goal: Identify what happens in the Orderflow *before* these events occur.

### Hypothesen (Signals to check)
For each detected Event (from Phase 1), analyze the **Pre-Event Window** (e.g., 10 mins before).

1.  **Delta Divergence:**
    *   Price makes Higher High, but CVD (Cumulative Volume Delta) makes Lower High? (Bearish)
    *   Price makes Lower Low, but CVD makes Higher Low? (Bullish/Absorption)
2.  **Volume Anomalies:**
    *   Is Volume > 3x average?
    *   Is Trade Count extremely high (Retail FOMO) or low (Whale Stealth)?
3.  **Liquidity / Orderbook:**
    *   Did the Spread widen significantly before the move?
    *   Did Imbalance shift?

---

## Phase 3: Validation & False Positives (Backtesting)
Goal: Validate the predictive power of found patterns. Avoid "Survivorship Bias".

**The Logic:**
It is not enough to say "Before every Crash, there was Pattern B". We must ask: "How often did Pattern B occur *without* a Crash following?"

### Methodology
1.  **Define Pattern B:** e.g., "Delta < 0 AND Price increasing for 3 minutes".
2.  **Scan Entire Dataset:** Find *all* occurrences of Pattern B.
3.  **Measure Outcome:** For each occurrence, look at the *next* 5 minutes. Did an Event (Pump/Crash) happen?
4.  **Metrics:**
    *   **True Positives (TP):** Pattern B followed by Event A.
    *   **False Positives (FP):** Pattern B followed by NO Event (or opposite move).
    *   **Precision:** `TP / (TP + FP)` -> The probability that the signal is correct.

Only patterns with a statistically significant Precision (> 55-60% or high Risk/Reward ratio) are candidates for trading bots or alerts.

---

## Phase 4: AI / LLM Integration
Once we have valid features (from Phase 2) and filtered dataset (Phase 3), we can feed this into models.
*   **LLM Agent:** "Analyze the last hour. Based on our proven 'Divergence Pattern', is there a setup forming?"

