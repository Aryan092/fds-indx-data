import pandas as pd
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "indx_data"
TICKERS = ["QQQ", "SPY"]

for ticker in TICKERS:
    m1_path = OUTPUT_DIR / f"{ticker}_1min.csv"
    if not m1_path.exists():
        print(f"Skipping {ticker}: {m1_path} not found")
        continue

    print(f"Computing intraday RV proxy for {ticker}...")
    df = pd.read_csv(m1_path, index_col="datetime", parse_dates=True)

    # 1-minute log returns
    df["log_ret"] = np.log(df["close"]) - np.log(df["close"].shift(1))

    # Rolling 30-minute realized variance (sum of squared log returns over past 30 bars)
    # This gives a "local volatility" estimate for each 1-minute bar
    window = 30
    df["rv_30m"] = df["log_ret"].rolling(window=window, min_periods=window).apply(
        lambda x: np.sqrt(np.sum(x ** 2)), raw=True
    )

    # Annualize: 30 minutes -> 390 minutes/day -> sqrt(390/30) = sqrt(13)
    df["rv_30m_ann"] = df["rv_30m"] * np.sqrt(390 / window)

    # Align to 5-minute grid by taking the RV at the END of each 5-minute window
    # (i.e., the 30-min RV computed from t-29 to t, assigned to the 5-min bar ending at t)
    m5_rv = df.groupby(pd.Grouper(freq="5min")).agg(
        rv_30m=("rv_30m", "last"),
        rv_30m_ann=("rv_30m_ann", "last"),
        avg_1m_vol=("rv_30m", "mean"),  # average of the 30m-RV across the 5-min window
    ).dropna(subset=["rv_30m"])

    out_path = OUTPUT_DIR / f"{ticker}_5min_rv_proxy.csv"
    m5_rv.to_csv(out_path)
    print(f"  Saved {len(m5_rv)} 5-min RV bars -> {out_path.name}")

print("Done.")
