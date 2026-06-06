import wrds
import pandas as pd
import numpy as np
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

WRDS_USER = "aryan"
TICKERS = ["SPY", "DIA", "IWB", "QQQ", "IWM"]
START_DATE = "2024-06-01"
END_DATE = "2025-12-31"
OUTPUT_DIR = Path(__file__).parent / "indx_data"
OUTPUT_DIR.mkdir(exist_ok=True)

def pull_one_ticker(ticker):
    conn = wrds.Connection(wrds_username=WRDS_USER, auto_commit=True)
    all_dates = pd.bdate_range(START_DATE, END_DATE)
    bars_1min = []
    bars_5min = []

    for i, date in enumerate(all_dates):
        date_str = date.strftime("%Y%m%d")
        year = date.year
        library = f"taqm_{year}"
        table = f"ctm_{date_str}"

        query_1min = f"""
            SELECT
                date,
                FLOOR((EXTRACT(HOUR FROM time_m)*60 + EXTRACT(MINUTE FROM time_m) - 570)) AS bar_idx,
                MIN(price) AS low, MAX(price) AS high, SUM(size) AS volume,
                (ARRAY_AGG(price ORDER BY time_m, time_m_nano ASC))[1] AS open_p,
                (ARRAY_AGG(price ORDER BY time_m, time_m_nano DESC))[1] AS close_p
            FROM {library}.{table}
            WHERE sym_root = '{ticker}'
              AND time_m >= '09:30:00' AND time_m < '16:00:00'
              AND (tr_corr = '' OR tr_corr = '00')
              AND price > 0
            GROUP BY date, FLOOR((EXTRACT(HOUR FROM time_m)*60 + EXTRACT(MINUTE FROM time_m) - 570))
        """

        try:
            df = conn.raw_sql(query_1min, date_cols=["date"])

            if not df.empty:
                mo = df["bar_idx"].astype(int) + 570
                h, m = mo // 60, mo % 60
                df["datetime"] = pd.to_datetime(
                    df["date"].dt.strftime("%Y-%m-%d") + " "
                    + h.astype(str).str.zfill(2) + ":"
                    + m.astype(str).str.zfill(2) + ":00"
                )
                df = df.set_index("datetime").sort_index()
                df = df[["open_p", "high", "low", "close_p", "volume"]]
                df.columns = ["open", "high", "low", "close", "volume"]
                bars_1min.append(df)

                m5 = df.groupby(pd.Grouper(freq="5min")).agg(
                    open=("open", "first"), high=("high", "max"),
                    low=("low", "min"), close=("close", "last"),
                    volume=("volume", "sum")
                ).dropna(subset=["open"])
                bars_5min.append(m5)

            if (i + 1) % 100 == 0 or (i + 1) == len(all_dates):
                print(f"  [{ticker}] {i+1}/{len(all_dates)}: {len(bars_1min)} days done, last={len(df) if not df.empty else 0} bars")
        except Exception as e:
            err = str(e)
            if "does not exist" in err or "permission denied" in err:
                pass
            elif (i + 1) % 100 == 0:
                print(f"  [{ticker}] {date_str}: error")

    conn.close()

    if not bars_1min:
        return None

    m1 = pd.concat(bars_1min).sort_index()
    m1 = m1[~m1.index.duplicated(keep="first")]
    m5 = pd.concat(bars_5min).sort_index()
    m5 = m5[~m5.index.duplicated(keep="first")]

    return m1, m5


def compute_volatility(m1_df, m5_df):
    if m1_df.empty:
        return pd.DataFrame()

    rows = []
    for date, grp in m1_df.groupby(m1_df.index.date):
        close = grp["close"].copy()
        returns = close.pct_change().dropna()
        rv = np.sqrt(np.sum(returns**2))
        rows.append({"date": date, "rv_daily_1m": rv, "rv_ann_1m": rv * np.sqrt(390)})
    m1_vol = pd.DataFrame(rows).set_index("date")

    rows = []
    for date, grp in m5_df.groupby(m5_df.index.date):
        close = grp["close"].copy()
        returns = close.pct_change().dropna()
        rv = np.sqrt(np.sum(returns**2))
        rows.append({"date": date, "rv_daily_5m": rv, "rv_ann_5m": rv * np.sqrt(78)})
    m5_vol = pd.DataFrame(rows).set_index("date")

    vol = m1_vol.join(m5_vol, how="outer")
    vol.index.name = "date"
    return vol.dropna()


print(f"Tickers: {TICKERS}")
print(f"Range: {START_DATE} to {END_DATE}")
print(f"Output: {OUTPUT_DIR}")
print(f"Running all tickers in parallel...\n")

t0 = time.time()

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(pull_one_ticker, t): t for t in TICKERS}

    for future in as_completed(futures):
        ticker = futures[future]
        try:
            result = future.result()
            if result:
                m1, m5 = result
                m1.to_csv(OUTPUT_DIR / f"{ticker}_1min.csv")
                m5.to_csv(OUTPUT_DIR / f"{ticker}_5min.csv")

                vol = compute_volatility(m1, m5)
                vol.to_csv(OUTPUT_DIR / f"{ticker}_volatility.csv")

                print(f"  [DONE] {ticker}: {len(m1):,} 1-min, {len(m5):,} 5-min, {len(vol):,} vol obs")
            else:
                print(f"  [FAIL] {ticker}: no data")
        except Exception as e:
            print(f"  [ERR] {ticker}: {e}")

print(f"\nTotal: {time.time()-t0:.1f}s")
print("All done!")