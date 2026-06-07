# Evaluation Summary: News-Driven Market Regimes Study

## Project Overview
**Working Title:** News-driven market regimes: A study on the effects of intraday market moving event arrivals on trading volume and volatility.

This project aims to quantify how real-time news events (specifically from the financial Twitter account **@FirstSquawk**) impact intraday market microstructure. The core goal is to develop a robust statistical pipeline that identifies abnormal market activity—"events"—and ultimately links them to the arrival of news headlines.

---

## Current Data Assets

### Market Data
- **ETFs:** QQQ, SPY, DIA, IWM, IWB
- **Resolutions:** 1-minute and 5-minute OHLCV bars
- **Auxiliary:** Daily volatility files for each ETF
- **Current focus in notebook:** QQQ 5-minute data only

### Tweet / News Data
- **Source:** FirstSquawk (financial news headline feed)
- **Total tweets:** ~167,000
  - Market hours (weekdays 09:30–16:00 ET): ~42,900
  - Outside market hours: ~124,400
- **Fields:** Tweet ID, New York Date, New York Timestamp, Headline Text, Twitter URL

---

## What the Notebooks Currently Do

### 1. Tweet Data Cleaning (`Tweet data cleaning.ipynb`)
- Loads raw FirstSquawk tweet data.
- Parses and standardizes timestamps to America/New_York timezone.
- Segregates tweets into **market-hours** and **outside-hours** datasets.
- Exports three cleaned CSV files for downstream use.

### 2. Data Analyses v0.1 (`Data analyses v0.1.ipynb`)
This is the core analysis notebook. It performs an **Event Study** to define and isolate market-moving periods.

#### A. Feature Engineering
Instead of using raw price/volume changes, the notebook constructs seasonality-adjusted features:
- **Absolute Log Returns:** Measures pure magnitude of intraday price disruption, agnostic to direction.
  $$R_t = \left| \ln\left(\frac{\text{Close}_t}{\text{Open}_t}\right) \right|$$
- **Parkinson Volatility:** Captures intra-period price swing within the 5-minute bar, superior to close-to-close volatility for high-frequency data.
  $$\text{Vol}_t = \frac{\left(\ln(\text{High}_t) - \ln(\text{Low}_t)\right)^2}{4 \ln 2}$$
- **Volume:** Raw volume as a proxy for institutional re-positioning.

#### B. Shock Index Construction
To avoid false positives from intraday seasonality (e.g., open/close naturally has higher volume/volatility), each feature is converted to a **Z-score** using a **20-day rolling lookback of the exact same 5-minute interval**. This means the 09:35 bar is only compared against previous 09:35 bars.

These Z-scores are fused into a single **Shock Index** via Euclidean distance:
$$\text{Shock Index} = \sqrt{(Z_{\text{Return}})^2 + (Z_{\text{Parkinson}})^2 + (Z_{\text{Volume}})^2}$$

This is a strong methodological choice because it accounts for nonstationarity and intraday periodicity.

#### C. Distribution & Threshold Analysis
- **Descriptive stats:** The shock index is extremely heavy-tailed (mean ~4.4, max ~5,926), indicating rare but massive outliers.
- **Intraday seasonality:** Plots show shock frequency and intensity vary significantly by time of day and day of week (e.g., higher near open/close, Monday effects).
- **Elbow method:** A threshold-selection curve is built to trade off event rarity vs. sample size.
- **Frequency mapping:** A percentile-to-frequency table translates thresholds into expected real-world occurrence rates (e.g., 99.7th percentile ≈ 1 event per week).

**Current stopping point:** The notebook defines *how* to find events but has not yet linked them to tweets.

---

## What the Project is Trying to Achieve (End-to-End Vision)
1. **Isolate statistically abnormal 5-minute windows** in market data using the shock index.
2. **Overlay the tweet timeline** to see if a FirstSquawk headline arrived just before or during the shock window.
3. **Quantify the impact** of these news-driven events on subsequent trading volume and realized volatility (an intraday event-study).
4. **Classify regimes:** Distinguish between "news-driven" shocks (preceded by a tweet) and "non-news-driven" shocks (algorithmic/technical), comparing their persistence and magnitude.
5. **Potentially build a predictive signal:** Can the arrival of certain tweet topics predict a shock in the next 1–3 bars?

---

## What More Can Be Done with Current Data

### Immediate Next Steps (No New Data Required)
1. **Merge Tweets with Shock Events**
   - The shock index exists. The tweet timestamps exist. The next logical step is a temporal join: for each shock event (e.g., Shock Index > 99.5th percentile), look back 1–3 intervals to see if a tweet arrived.
2. **Use Other ETFs**
   - Data already exists for SPY, DIA, IWM, IWB. Compute the shock index for all of them. This allows:
     - Cross-asset contagion analysis (does a QQQ shock spill over to IWM/SPY?)
     - Sector-specific news identification (is the news tech-specific or macro?)
3. **Lead-Lag Analysis**
   - Measure the precise lag between tweet timestamp and the peak of the shock index. Does the market digest FirstSquawk news instantly (same 5-min bar) or with a 5–15 minute lag?
4. **Event-Study Response Curves**
   - For windows around a shock, plot cumulative abnormal volume (CAV) and cumulative abnormal volatility around the event time (t-5 to t+10 bars).
5. **Outside-Hours Tweet Analysis**
   - 124k tweets occur outside market hours. Study whether these predict the next morning's open volatility or overnight gap size.
6. **Volatility File Integration**
   - The `QQQ_volatility.csv` (and others) have not yet been used. These could serve as a daily benchmark or to compute volatility-of-volatility.
7. **Topic / Keyword Bucketing**
   - Even without sophisticated NLP, simple regex or keyword filtering on headlines (e.g., "FED", "EARNINGS", "TARIFF", "WAR", "OIL") can segment tweets into categories to compare shock impact by news type.
8. **Day-of-Week / Time-of-Day Conditioning**
   - The heatmaps show structural differences. Condition the event study on these (e.g., are Monday morning news shocks more persistent than Friday afternoon ones?).
9. **Shock Persistence / Decay**
   - After a shock event, how many bars does it take for volume/volatility to revert to its 20-day baseline for that time slot?
10. **False Positive Audit**
    - Manually inspect a random sample of shock events that had *no* preceding tweet. Are they explainable by technical breaks, large block trades, or index rebalancing? This helps calibrate the threshold.

---

## What Other Data Can Add Value

### High-Priority / High-Impact
1. **Scheduled Macro Economic Calendar**
   - FOMC announcements, CPI/PPI releases, Non-Farm Payrolls, Treasury auctions. These are the biggest confounders. A shock at 8:30 AM or 2:00 PM may be a scheduled release, not a FirstSquawk headline. Need to control for them.
2. **Earnings Calendar**
   - QQQ is tech-heavy. Major earnings (AAPL, MSFT, NVDA, etc.) drive massive intraday volume/volatility. Need to know if a shock coincided with a constituent's earnings release.
3. **VIX & VIX Futures (Term Structure)**
   - The VIX reacts faster and more cleanly to macro uncertainty than QQQ sometimes does. It provides a market-implied volatility benchmark and can help distinguish fear-driven from liquidity-driven shocks.
4. **Order Book / Tick-Level Data (TAQ or similar)**
   - If available, bid-ask spread, order flow imbalance, and depth would reveal *how* the market microstructure breaks during a shock (e.g., widening spreads, asymmetric order flow).

### Medium-Priority / Enriching
5. **Broader News Feeds**
   - Bloomberg headlines, Dow Jones Newswires, Reuters. FirstSquawk is fast, but verifying with institutional feeds adds robustness and reduces single-source bias.
6. **Alternative Social Data**
   - Reddit (r/WallStreetBets), StockTwits, or Twitter/X sentiment aggregates. Useful for gauging retail vs. institutional reaction.
7. **Cross-Asset Price Data**
   - Treasury yields (TLT, 10Y futures), USD index (DXY), Commodities (Gold, Oil), Bitcoin. Helps determine if a shock is idiosyncratic to equities or part of a broader macro risk-off/risk-on move.
8. **SEC Filings (Form 8-K, 10-Q, 13F)**
   - For stock-specific or ETF-creation/redemption flows. Especially useful if analyzing individual QQQ constituents.
9. **ETF Flow / Creation-Redemption Data**
   - Daily authorized participant (AP) creation/redemption baskets for QQQ. Large flows often precede or accompany volume spikes.
10. **Implied Volatility Surface (QQQ Options)**
    - Allows decomposition of shocks into realized vs. implied volatility changes. Did the option market price in the risk before the tweet?

### Lower-Priority / Long-Term
11. **Institutional Positioning (CFTC COT, 13F)**
    - Slow-moving, but useful for regime context (e.g., are funds already max-long, making them forced sellers on bad news?).
12. **Market Sentiment Indices**
    - AAII sentiment, Fear & Greed index, Consumer Confidence. Useful for conditioning the analysis on prevailing bullish/bearish sentiment.
13. **Insider Transactions**
    - Relevant if the study ever narrows down to single-stock events within the ETF.

---

## Methodological Recommendations
1. **Threshold Selection:** The 99.5%–99.7% range (≈1–2 events per week) is a well-reasoned starting point, but consider using a **two-threshold system**:
   - A **lower threshold** to flag "potential" events for tweet-scanning.
   - A **higher threshold** to confirm "major" events for the event-study.
2. **Causality Caution:** Correlating tweets with shocks does not prove causality. A tweet may simply *report* a price move already underway. Use **Granger causality** tests or carefully defined lead-lag windows (tweet must arrive *before* the shock peak).
3. **Control Group:** The notebook hints at this. Explicitly compare "news-driven" shocks vs. "non-news-driven" shocks. If the tweet truly matters, the former should exhibit higher persistence and larger post-event volume/volatility.
4. **Multiple Hypothesis Testing:** If testing many tweet categories or thresholds, apply Bonferroni or FDR corrections to avoid false discovery.

---

## Summary
The project has established a **solid quantitative foundation** for identifying abnormal intraday market events. The shock index methodology is statistically sound and properly handles intraday seasonality. The immediate bottleneck is not a lack of data, but the **next analytical layer**: linking the tweet timestamps to the shock events and measuring the differential impact of news-driven vs. non-news-driven volatility.

The biggest risk to validity right now is **omitted variable bias**—shocks may be caused by scheduled macro announcements or earnings rather than FirstSquawk headlines. Acquiring a macro/earnings calendar should be the highest-priority external data addition.

---

# Data Acquisition Plan: 4 High-Priority Datasets

This plan is designed around the project's **existing infrastructure**:
- WRDS access (`aryan`) with TAQ (`taqm_YYYY.ctm_YYYYMMDD`)
- Python tooling (`wrds`, `pandas`, `numpy`, `yfinance`)
- CSV-based storage in `indx_data/`
- Date range: **2024-06-01 to 2025-12-31**

---

## 1. Scheduled Macro Economic Calendar

### What & Why
FOMC decisions, CPI/PPI, Non-Farm Payrolls, Retail Sales, GDP, ISM, and Treasury auctions. These are the **largest confounders** in the study. A volume/volatility spike at 08:30 or 14:00 ET is often a scheduled macro release, not a tweet-driven event. Controlling for them is essential for causal validity.

### Recommended Approach
**Hybrid: Manual curation + FRED automation for a short date range.**

Because the project only covers ~1.5 years, manually curating a CSV of ~40 major events is faster, more reliable, and more reproducible than building a scraper.

| Event | Typical Release (ET) | FRED Series / Source |
|-------|------------------------|----------------------|
| FOMC Rate Decision | 14:00 (pre-2025) / 14:00 | federalreserve.gov |
| CPI (YoY/MoM) | 08:30 | `CPIAUCSL` |
| PPI | 08:30 | `PPIACO` |
| Non-Farm Payrolls | 08:30 | `PAYEMS` |
| Retail Sales | 08:30 | `RSXFS` |
| GDP (Advance) | 08:30 | `GDP` |
| ISM Manufacturing | 10:00 | `NAPM` |
| Jobless Claims | 08:30 | `ICSA` |

**Step-by-step:**
1. Create a Python script `pull_macro_calendar.py`.
2. Use `pandas_datareader.DataReader` with the FRED API to pull release dates for the series above. The date index in FRED corresponds to the *publication date*.
3. Manually augment with FOMC meeting dates (from [federalreserve.gov/monetarypolicy/fomccalendars.htm](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm))—there are only ~12 meetings in the window.
4. Output a single CSV with columns: `event_name`, `date`, `time_et`, `importance`.

**Integration:**
- In the event-study notebook, add a `is_macro_window` flag: for any shock event, check if `event_time` falls within ±15 minutes of a macro release. If yes, classify the shock as `macro-driven` rather than `tweet-driven`.

**Effort:** Low (1–2 hours). No new API keys needed if using FRED (free, no key required for `pandas_datareader`).

---

## 2. Earnings Calendar

### What & Why
QQQ is heavily weighted toward mega-cap tech (AAPL, MSFT, NVDA, etc.). Their earnings releases cause massive, predictable intraday volume and volatility spikes. Without controlling for earnings, the shock index will falsely attribute these to unrelated tweets.

### Recommended Approach
**WRDS IBES (Institutional Brokers' Estimate System).**

Since the project already has a WRDS connection, IBES is the most precise academic source for earnings announcement dates and times.

**Step-by-step:**
1. First, obtain the QQQ constituent list. Use a static Nasdaq 100 list for 2024–2025, or query WRDS CRSP (`crsp.dsenames`) for historical constituents.
2. Connect to WRDS and query `ibes.act_epsus` (Actual EPS—US).
   ```sql
   SELECT ticker, anndats, anntims, value, pdc
   FROM ibes.act_epsus
   WHERE ticker IN ('AAPL','MSFT','NVDA',...)
     AND anndats BETWEEN '2024-06-01' AND '2025-12-31'
   ```
3. The `anndats` field is the announcement date; `anntims` is the announcement time (e.g., `BTO` = Before Open, `AMC` = After Market Close, or exact HH:MM).
4. Clean the time field into a standardized timestamp (` America/New_York`).
5. Export to `indx_data/earnings_calendar.csv`.

**Alternative (if IBES is unavailable):**
- Use `yfinance` to pull earnings dates for each QQQ ticker via `yf.Ticker("AAPL").earnings_dates`. This gives dates but not always exact times. Less precise, but free.

**Integration:**
- Similar to macro: flag any shock window that coincides with a top-10 QQQ weight earnings release (±30 mins for BTO/AMC, ±15 mins for intraday).
- Consider weighting by market-cap impact—an AAPL earnings surprise moves QQQ more than a small Nasdaq 100 constituent.

**Effort:** Medium (2–3 hours). Requires verifying WRDS IBES subscription access.

---

## 3. VIX & VIX Futures (Term Structure)

### What & Why
VIX is a market-implied volatility index that reacts faster and more cleanly to macro uncertainty than equity ETFs. Adding VIX allows you to:
- Distinguish **fear-driven** shocks (VIX spikes simultaneously) from **liquidity-driven** or **idiosyncratic** shocks.
- Use the **VIX futures term structure** (front month vs. second month) to measure whether the market expects volatility to persist (backwardation) or mean-revert (contango).

### Recommended Approach
**VIX Spot (Daily):** FRED API (`VIXCLS`) or CBOE.
**VIX Futures (Daily Term Structure):** CBOE historical downloads or `yfinance`.

**Step-by-step:**

**A. VIX Spot (Daily Close)**
```python
from pandas_datareader.data import DataReader
vix = DataReader("VIXCLS", "fred", start="2024-06-01", end="2025-12-31")
vix.to_csv("indx_data/VIX_daily.csv")
```

**B. VIX Futures (Daily)**
- CBOE provides free historical VIX futures settlement prices: [www.cboe.com/tradable_products/vix/vix_historical_data/](https://www.cboe.com/tradable_products/vix/vix_historical_data/)
- Download the monthly zip files for 2024–2025, unzip, and merge into a single CSV.
- If automating, `yfinance` can pull continuous front-month futures (`VX=F`) and specific expirations (e.g., `VXF25.CBT`). Note: Yahoo Finance symbols vary.
```python
import yfinance as yf
vx_front = yf.download("VX=F", start="2024-06-01", end="2025-12-31", interval="1d")
```

**C. Intraday VIX (if desired)**
- `yfinance` supports 1-minute data for `^VIX` (the index itself) over 7-day windows.
- For intraday futures, CBOE's data is typically daily only unless you have a futures data subscription (e.g., Polygon.io, IQFeed). Given the project's date range, daily VIX + futures is sufficient for control variables.

**Storage:**
- `indx_data/VIX_daily.csv` (spot)
- `indx_data/VIX_futures_term_structure.csv` (columns: `date`, `front_month`, `second_month`, `third_month`, ...)

**Integration:**
- Merge daily VIX spot with the daily realized volatility files (`QQQ_volatility.csv`) to compare realized vs. implied vol.
- In the event study, condition on the VIX level or term-structure slope (front / second_month ratio). A shock during high VIX + backwardation is likely macro, not tweet-specific.

**Effort:** Low–Medium (1–2 hours for spot + manual CBOE download; 3–4 hours if automating futures).

---

## 4. Order Book / Tick-Level Quote Data

### What & Why
The current script pulls **Consolidated Trades** (`ctm`) from WRDS TAQ. To see *how* the market microstructure breaks during a shock, you need **Consolidated Quotes** (`cqm`)—specifically the National Best Bid and Offer (NBBO). This enables:
- **Relative Bid-Ask Spread:** `(ask - bid) / mid`
- **Quote Intensity:** Number of quote updates per bar (proxy for attention/activitiy)
- **Order Flow Imbalance:** Buyer-initiated vs. seller-initiated volume using the Lee-Ready algorithm or quote midpoint rule

### Recommended Approach
**Extend the existing `pull_indx_data.py` to also query `taqm_YYYY.cqm_YYYYMMDD`.**

This is the most natural extension because it uses the exact same WRDS connection, date loop, and threading pattern already in place.

**Step-by-step:**
1. Duplicate the `pull_one_ticker` logic into a new function `pull_one_ticker_quotes(ticker)`.
2. Change the SQL to target the quote tables:
   ```sql
   SELECT
       date,
       time_m,
       time_m_nano,
       bid,
       bidsiz,
       ask,
       asksiz
   FROM taqm_YYYY.cqm_YYYYMMDD
   WHERE sym_root = '{ticker}'
     AND time_m >= '09:30:00' AND time_m < '16:00:00'
   ```
3. Aggregate to 1-minute / 5-minute bars:
   ```python
   grp = quotes_df.groupby(pd.Grouper(freq="1min"))
   quote_bars = grp.agg(
       avg_spread = ((quotes_df['ask'] - quotes_df['bid']) / ((quotes_df['ask'] + quotes_df['bid'])/2)).mean(),
       quote_count = ('bid', 'size'),  # number of updates
       best_bid = ('bid', 'last'),
       best_ask = ('ask', 'last')
   )
   ```
4. Merge trade bars and quote bars on `datetime` index.
5. Compute **order flow imbalance** (requires matching trades to quotes):
   - Use the **quote midpoint rule**: a trade is buyer-initiated if `price > quote_midpoint` at the time of execution; seller-initiated if `price < midpoint`.
   - Aggregate `buy_volume - sell_volume` per 5-minute bar.

**Storage:**
- Either append columns to the existing `QQQ_5min.csv` (`spread`, `quote_count`, `of_imba`) or save side-by-side as `QQQ_5min_micro.csv`.

**Integration:**
- Add **bid-ask spread** as a fourth feature in the Shock Index (normalized by 20-day rolling baseline for that interval). Spikes in spread are a direct measure of market stress.
- Use **order flow imbalance** in the event study: did the tweet trigger one-sided selling pressure?

**Caveat:**
- TAQ quote tables (`cqm`) are **significantly larger** than trade tables (`ctm`). A parallel ThreadPoolExecutor is essential, but expect longer download times (2–4×).
- `bidsiz` and `asksiz` in TAQ represent the depth at the NBBO, not full book depth. This is sufficient for spread and basic imbalance, but not full L2/L3 analysis.

**Effort:** Medium–High (4–6 hours). Requires testing the quote query on a single date first to verify WRDS permissions and table structure.

---

## Summary Table

| Priority | Dataset | Primary Source | Effort | Key Integration |
|----------|---------|---------------|--------|----------------|
| 1 | Macro Calendar | FRED + manual FOMC | Low | Exclude/flag shocks at release times |
| 2 | Earnings Calendar | WRDS IBES (`ibes.act_epsus`) | Medium | Exclude shocks around mega-cap earnings |
| 3 | VIX & Futures | FRED (spot) + CBOE/yfinance (futures) | Low–Medium | Control for macro volatility regime |
| 4 | Order Book Quotes | WRDS TAQ (`cqm_YYYYMMDD`) | Medium–High | Add spread + OFI to shock index & event study |

**Recommended execution order:**
1. **Macro calendar** (fastest, highest causal payoff)
2. **Earnings calendar** (second-fastest, critical for QQQ)
3. **VIX spot** (5-minute FRED pull)
4. **VIX futures** (if daily control is enough, manual CBOE download; skip if overkill)
5. **TAQ quotes** (largest effort, do this only after the core tweet-shock linkage is working)

This order ensures the omitted-variable problem is fixed before investing in microstructure depth.

---

# Execution Notes

All four high-priority data acquisition scripts have been executed. Below is a summary of what was produced, issues encountered, and how to integrate the new data.

---

## Scripts Created

| Script | Purpose |
|--------|---------|
| `pull_macro_calendar.py` | Generates `macro_calendar.csv` from verified BLS/BEA/Fed release dates |
| `pull_vix.py` | Downloads VIX spot via `yfinance` |
| `pull_earnings.py` | Pulls earnings dates via WRDS IBES (fallback: `yfinance`) |
| `pull_quotes.py` | Pulls TAQ NBBO quote bars from WRDS `complete_nbbo_YYYY` master tables |

---

## Files Produced in `indx_data/`

### Macro Calendar
- **File:** `macro_calendar.csv` (7.1 KB)
- **Records:** 197 scheduled macro events
- **Events included:**
  - FOMC Meetings (13 dates, 14:00 ET)
  - CPI (19 dates, 08:30 ET)
  - PPI (19 dates, 08:30 ET)
  - Non-Farm Payrolls (~22 first-Fridays, 08:30 ET)
  - Retail Sales (19 dates, 08:30 ET)
  - ISM Manufacturing (monthly first business day, 10:00 ET)
  - Jobless Claims (weekly Thursdays, 08:30 ET)
  - GDP Advance (quarterly, 08:30 ET)
- **Issue:** Fed website scrape returned HTTP 403; script used fallback hardcoded FOMC dates from verified public records.
- **Integration:** Load `macro_calendar.csv`, create a `datetime` column from `datetime` + `time_et`, and flag any shock event whose timestamp is within ±15 minutes of a macro release.

### Earnings Calendar
- **File:** `earnings_calendar.csv` (4.5 KB)
- **Records:** 184 earnings dates for 30 top QQQ constituents
- **Tickers covered:** AAPL, MSFT, NVDA, AMZN, META, AVGO, TSLA, COST, NFLX, GOOGL, GOOG, TMUS, AMD, PEP, LIN, ADBE, CSCO, INTC, QCOM, TXN, HON, AMGN, SBUX, INTU, GILD, ADI, BKNG, LRCX, MU, PANW
- **Issue:** WRDS IBES query failed because column `pdc` does not exist in `ibes.act_epsus`. Script successfully fell back to `yfinance`.
- **Limitation:** `yfinance` returns dates but not exact announcement times (BTO/AMC/intraday). For the event study, assume ±30-minute window around market open/close on the earnings date for BTO/AMC classification.
- **Integration:** Flag any shock window that falls on an earnings date for a top-10 QQQ constituent.

### VIX
- **File:** `VIX_daily.csv` (33 KB)
- **Records:** 396 daily observations (OHLC)
- **Issue:** VIX futures front-month and second-month symbols (`VX=F`, `VXM25.CBT`, etc.) are not available on Yahoo Finance. Only VIX spot was successfully downloaded.
- **Workaround:** For term-structure analysis, manual CBOE download is required. For the current event-study scope, daily VIX spot is sufficient as a macro-volatility control.
- **Integration:** Merge `VIX_daily.csv` with daily realized volatility files (e.g., `QQQ_volatility.csv`) to compute realized vs. implied vol gaps. Condition the event study on whether the shock occurred during elevated VIX (>20 or >30).

#### Intraday VIX Proxies
True historical VIX index (^VIX) at 1-minute granularity for 2024–2025 is **not freely available** (Yahoo limits 1m data to 7 days; WRDS CBOE library is daily-only with some permission restrictions). Two intraday alternatives were pulled instead:

**A. VIX Futures ETFs (TAQ 1-min / 5-min)**
These trade like regular equities and were pulled via the same WRDS TAQ pipeline used for QQQ/SPY.

| Ticker | Proxy For | 1-min bars | 5-min bars | Daily Vol File |
|--------|-----------|-----------|-----------|----------------|
| **VIXY** | Medium-term VIX futures | 151,506 | 30,899 | `VIXY_volatility.csv` |
| **UVXY** | 1.5× short-term VIX futures | 154,541 | 30,958 | `UVXY_volatility.csv` |
| **SVXY** | Inverse short-term VIX futures | 146,914 | 30,813 | `SVXY_volatility.csv` |

- **UVXY** is the most sensitive (leveraged) and reacts fastest to intraday volatility regime shifts.
- **Caveat:** These ETFs suffer from contango/decay over long horizons, but for intraday windows (a few 5-minute bars), they track VIX futures movements closely.
- **Integration:** Add UVXY/VIXY returns as control variables. If QQQ spikes and UVXY spikes simultaneously, the shock is likely macro/fear-driven rather than tweet-specific.

**B. Realized Volatility Proxy (computed from existing 1-min QQQ/SPY)**
A rolling 30-minute realized volatility was computed and aligned to the 5-minute grid.

| File | Contents |
|------|----------|
| `QQQ_5min_rv_proxy.csv` | 30,960 bars: `rv_30m`, `rv_30m_ann`, `avg_1m_vol` |
| `SPY_5min_rv_proxy.csv` | 30,960 bars: same |

- `rv_30m` = √Σ(log returns²) over the past 30 1-minute bars, assigned to the end of each 5-minute window.
- This is a **pure realized volatility** measure of the actual asset being traded. Unlike VIX (implied from SPX options), this tells you what volatility actually *happened* in QQQ over the last 30 minutes.
- **Integration:** Can be added as an additional feature in the Shock Index, or used to normalize shock magnitude (a 2σ shock when 30m-RV is already elevated may be less meaningful than when RV is low).

### TAQ NBBO Quote Bars
- **Files per ticker:**
  - `{ticker}_1min_quotes.csv` (raw 1-min NBBO aggregates)
  - `{ticker}_5min_quotes.csv` (5-min NBBO aggregates)
  - `{ticker}_5min_micro.csv` (**merged trades + quotes**)
- **Tickers:** SPY, DIA, IWB, QQQ, IWM
- **Records per ticker:** ~154,000 1-min bars; ~31,000 5-min bars
- **Columns in `_5min_micro.csv`:**
  - Trade OHLCV (existing)
  - `best_bid_open/high/low/close`, `best_ask_open/high/low/close`
  - `avg_spread` (dollar average)
  - `avg_mid` (dollar average)
  - `quote_count` (number of NBBO changes in the 5-min window)
  - `mid` (closing midpoint)
  - `rel_spread` (relative spread = (ask - bid) / mid)
  - `spread_bps` (relative spread in basis points)
- **Implementation detail:** Instead of pulling raw `cqm` daily tables (which would require ~2M rows/day and 80+ seconds per day), the script queries the WRDS **yearly master table** `taqm_YYYY.complete_nbbo_YYYY`, aggregating directly to 1-minute bars in SQL. This reduced the query time to ~0.4 seconds per trading day.
- **Total execution time:** ~7 minutes for all 5 tickers (3 parallel workers).
- **Integration:**
  - Add `rel_spread` (or `spread_bps`) as a fourth feature in the Shock Index (Z-score it against the same 5-min interval over 20 days, just like returns/vol/volume).
  - Use `quote_count` as a proxy for market attention/activity during a shock window.
  - Use `best_bidsizeshares` / `best_asksizeshares` (currently in `_1min_quotes.csv`) to compute depth imbalance if needed.

---

## Next Immediate Steps

With the new data in place, the notebook can now be extended:

1. **Shock Index v2.0**
   - Include `rel_spread` as the fourth component.
   - Recompute the Shock Index and re-evaluate the threshold distribution.

2. **Confounder Filtering**
   - Before linking tweets to shocks, filter out shocks that occur within ±15 minutes of a macro release or on a major earnings date.
   - This isolates the "true tweet-driven" shock subset.

3. **Tweet-Shock Temporal Join**
   - For each remaining shock event (after confounder filtering), scan the `firstsquawk_market_hours.csv` timeline for a headline within the preceding 1–3 five-minute bars.
   - Compute the proportion of shocks preceded by a tweet (news-driven vs. non-news-driven).

4. **VIX Conditioning**
   - Merge daily VIX spot into the event-study DataFrame.
   - Compare tweet-shock impact during low-VIX (<15) vs. high-VIX (>25) regimes.
