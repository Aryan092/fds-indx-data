import wrds
import pandas as pd
import numpy as np
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

WRDS_USER = "aryan"
TICKERS = ["SPY", "DIA", "IWB", "QQQ", "IWM"]
START_DATE = "2024-06-01"
END_DATE = "2025-12-31"
OUTPUT_DIR = Path(__file__).parent / "indx_data"
OUTPUT_DIR.mkdir(exist_ok=True)


def pull_one_ticker_quotes(ticker):
    """
    Pull TAQ NBBO quotes for a single ticker using yearly master tables,
    aggregate to 1-min bars in SQL, then to 5-min bars in Python.
    """
    conn = wrds.Connection(wrds_username=WRDS_USER, auto_commit=True)
    quotes_1min = []

    years = [2024, 2025]
    for year in years:
        year_start = max(START_DATE, f"{year}-01-01")
        year_end = min(END_DATE, f"{year}-12-31")
        table = f"taqm_{year}.complete_nbbo_{year}"

        query = f"""
            SELECT
                date,
                FLOOR((EXTRACT(HOUR FROM time_m)*60 + EXTRACT(MINUTE FROM time_m) - 570)) AS bar_idx,
                MIN(best_bid) AS best_bid_low,
                MAX(best_bid) AS best_bid_high,
                MIN(best_ask) AS best_ask_low,
                MAX(best_ask) AS best_ask_high,
                AVG(best_ask - best_bid) AS avg_spread,
                AVG((best_ask + best_bid)/2.0) AS avg_mid,
                COUNT(*) AS quote_count
            FROM {table}
            WHERE sym_root = '{ticker}'
              AND date BETWEEN '{year_start}' AND '{year_end}'
              AND time_m >= '09:30:00' AND time_m < '16:00:00'
              AND best_bid > 0 AND best_ask > 0
            GROUP BY date, FLOOR((EXTRACT(HOUR FROM time_m)*60 + EXTRACT(MINUTE FROM time_m) - 570))
            ORDER BY date, bar_idx
        """

        try:
            t0 = time.time()
            df = conn.raw_sql(query, date_cols=["date"])
            elapsed = time.time() - t0
            if df.empty:
                print(f"  [{ticker}] {year}: no data ({elapsed:.1f}s)")
                continue

            # Reconstruct datetime index from date + bar_idx
            df["bar_idx"] = df["bar_idx"].astype(int)
            mo = df["bar_idx"] + 570
            h, m = mo // 60, mo % 60
            df["datetime"] = pd.to_datetime(
                df["date"].dt.strftime("%Y-%m-%d")
                + " "
                + h.astype(str).str.zfill(2)
                + ":"
                + m.astype(str).str.zfill(2)
                + ":00"
            )
            df = df.set_index("datetime").sort_index()
            df = df.drop(columns=["date", "bar_idx"])
            quotes_1min.append(df)
            print(f"  [{ticker}] {year}: {len(df)} 1-min bars ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  [{ticker}] {year}: error - {e}")

    conn.close()

    if not quotes_1min:
        return None

    q1 = pd.concat(quotes_1min).sort_index()
    q1 = q1[~q1.index.duplicated(keep="first")]

    # Aggregate 1-min quote bars to 5-min bars
    q5 = q1.groupby(pd.Grouper(freq="5min")).agg(
        best_bid_open=("best_bid_low", "first"),
        best_bid_high=("best_bid_high", "max"),
        best_bid_low=("best_bid_low", "min"),
        best_bid_close=("best_bid_high", "last"),
        best_ask_open=("best_ask_low", "first"),
        best_ask_high=("best_ask_high", "max"),
        best_ask_low=("best_ask_low", "min"),
        best_ask_close=("best_ask_high", "last"),
        avg_spread=("avg_spread", "mean"),
        avg_mid=("avg_mid", "mean"),
        quote_count=("quote_count", "sum"),
    ).dropna(subset=["best_bid_open"])

    return q1, q5


def merge_with_trades(ticker, q5_df):
    """Merge 5-min quote bars with existing 5-min trade bars."""
    trade_path = OUTPUT_DIR / f"{ticker}_5min.csv"
    if not trade_path.exists():
        print(f"  [{ticker}] trade file not found, skipping merge.")
        return

    trades = pd.read_csv(trade_path, index_col="datetime", parse_dates=True)
    merged = trades.join(q5_df, how="left")
    merged["mid"] = (merged["best_bid_close"] + merged["best_ask_close"]) / 2
    merged["rel_spread"] = (merged["best_ask_close"] - merged["best_bid_close"]) / merged["mid"]
    merged["spread_bps"] = merged["rel_spread"] * 10000
    out_path = OUTPUT_DIR / f"{ticker}_5min_micro.csv"
    merged.to_csv(out_path)
    print(f"  [{ticker}] merged trades + quotes -> {out_path.name}")


print(f"Tickers: {TICKERS}")
print(f"Range: {START_DATE} to {END_DATE}")
print(f"Output: {OUTPUT_DIR}")
print(f"Running quote pull in parallel (max 3 workers)...\n")

t0 = time.time()

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(pull_one_ticker_quotes, t): t for t in TICKERS}

    for future in as_completed(futures):
        ticker = futures[future]
        try:
            result = future.result()
            if result:
                q1, q5 = result
                q1.to_csv(OUTPUT_DIR / f"{ticker}_1min_quotes.csv")
                q5.to_csv(OUTPUT_DIR / f"{ticker}_5min_quotes.csv")
                print(f"[DONE] {ticker}: {len(q1):,} 1-min, {len(q5):,} 5-min quote bars")
                merge_with_trades(ticker, q5)
            else:
                print(f"[FAIL] {ticker}: no quote data")
        except Exception as e:
            print(f"[ERR] {ticker}: {e}")

print(f"\nTotal: {time.time()-t0:.1f}s")
print("Quote pull complete!")
