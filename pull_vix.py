import yfinance as yf
import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "indx_data"
OUTPUT_DIR.mkdir(exist_ok=True)

START_DATE = "2024-06-01"
END_DATE = "2025-12-31"


def flatten_yf(df):
    """Flatten yfinance MultiIndex columns (Price, Ticker) -> simple columns."""
    if isinstance(df.columns, pd.MultiIndex):
        # Drop the Ticker level (level 1), keep Price level (level 0)
        df.columns = df.columns.droplevel(1)
    return df


# 1. VIX Spot (Daily close) from yfinance (ticker ^VIX)
print("Pulling VIX spot (^VIX)...")
vix_spot = yf.download("^VIX", start=START_DATE, end=END_DATE, interval="1d", auto_adjust=False)
if not vix_spot.empty:
    vix_spot = flatten_yf(vix_spot)
    vix_spot = vix_spot[["Open", "High", "Low", "Close"]]
    vix_spot.columns = ["open", "high", "low", "close"]
    vix_spot.index.name = "date"
    vix_spot.to_csv(OUTPUT_DIR / "VIX_daily.csv")
    print(f"  VIX spot: {len(vix_spot)} rows -> VIX_daily.csv")
else:
    print("  VIX spot download failed.")

# 2. VIX Futures (front month continuous contract)
# Yahoo Finance symbol: VX=F (CBOE VIX Front Month Futures)
print("Pulling VIX futures front month (VX=F)...")
vx_front = yf.download("VX=F", start=START_DATE, end=END_DATE, interval="1d", auto_adjust=False)
if not vx_front.empty:
    vx_front = flatten_yf(vx_front)
    vx_front = vx_front[["Open", "High", "Low", "Close"]]
    vx_front.columns = ["open", "high", "low", "close"]
    vx_front.index.name = "date"
    vx_front.to_csv(OUTPUT_DIR / "VIX_futures_front.csv")
    print(f"  VIX futures front: {len(vx_front)} rows -> VIX_futures_front.csv")
else:
    print("  VIX futures front download failed.")

# 3. VIX Futures second month (if available)
# Yahoo symbols vary by expiry; try a common near-term symbol
print("Pulling VIX futures second month (attempt)...")
for sym in ["VXM25.CBT", "VXN25.CBT", "VXF25.CBT"]:
    vx2 = yf.download(sym, start=START_DATE, end=END_DATE, interval="1d", auto_adjust=False)
    if not vx2.empty:
        vx2 = flatten_yf(vx2)
        vx2 = vx2[["Open", "High", "Low", "Close"]]
        vx2.columns = ["open", "high", "low", "close"]
        vx2.index.name = "date"
        vx2.to_csv(OUTPUT_DIR / "VIX_futures_second.csv")
        print(f"  VIX futures second: {len(vx2)} rows -> VIX_futures_second.csv (symbol={sym})")
        break
else:
    print("  No VIX futures second month symbol succeeded (this is expected; symbols vary by expiry).")

print("VIX data pull complete.")
