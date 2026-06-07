import wrds
import pandas as pd
from pathlib import Path
import yfinance as yf
import time

OUTPUT_DIR = Path(__file__).parent / "indx_data"
OUTPUT_DIR.mkdir(exist_ok=True)

WRDS_USER = "aryan"
START_DATE = "2024-06-01"
END_DATE = "2025-12-31"

# QQQ top constituents (approximate, covers the heavy hitters)
QQQ_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "TSLA", "COST", "NFLX", "GOOGL",
    "GOOG", "TMUS", "AMD", "PEP", "LIN", "ADBE", "CSCO", "INTC", "QCOM", "TXN",
    "HON", "AMGN", "SBUX", "INTU", "GILD", "ADI", "BKNG", "LRCX", "MU", "PANW"
]


def pull_ibes():
    """Try WRDS IBES for exact earnings announcement dates/times."""
    try:
        conn = wrds.Connection(wrds_username=WRDS_USER, auto_commit=True)
        tickers_str = ",".join([f"'{t}'" for t in QQQ_TICKERS])
        query = f"""
            SELECT ticker, anndats, anntims, value, pdc
            FROM ibes.act_epsus
            WHERE ticker IN ({tickers_str})
              AND anndats BETWEEN '{START_DATE}' AND '{END_DATE}'
            ORDER BY ticker, anndats
        """
        df = conn.raw_sql(query, date_cols=["anndats"])
        conn.close()
        if df.empty:
            print("  IBES returned no data.")
            return pd.DataFrame()
        df = df.rename(columns={"anndats": "date", "anntims": "time_flag", "value": "eps_actual", "pdc": "eps_consensus"})
        df["source"] = "WRDS_IBES"
        return df
    except Exception as e:
        print(f"  IBES pull failed: {e}")
        return pd.DataFrame()


def pull_yfinance_earnings():
    """Fallback: use yfinance to get earnings dates for each ticker."""
    all_dates = []
    for ticker in QQQ_TICKERS:
        try:
            t = yf.Ticker(ticker)
            cal = t.earnings_dates
            if cal is None or cal.empty:
                continue
            cal = cal.reset_index()
            # yfinance returns index as datetime and columns vary by version
            date_col = "Earnings Date" if "Earnings Date" in cal.columns else cal.columns[0]
            cal = cal.rename(columns={date_col: "date"})
            cal["date"] = pd.to_datetime(cal["date"]).dt.tz_localize(None).dt.normalize()
            cal = cal[(cal["date"] >= START_DATE) & (cal["date"] <= END_DATE)]
            cal["ticker"] = ticker
            cal["source"] = "yfinance"
            all_dates.append(cal[["ticker", "date", "source"]])
            time.sleep(0.3)  # be polite
        except Exception as e:
            print(f"  yfinance failed for {ticker}: {e}")
    if not all_dates:
        return pd.DataFrame()
    df = pd.concat(all_dates, ignore_index=True)
    return df.drop_duplicates(subset=["ticker", "date"]).sort_values(["ticker", "date"]).reset_index(drop=True)


if __name__ == "__main__":
    print("Pulling earnings calendar...")
    earnings = pull_ibes()
    if earnings.empty:
        print("Falling back to yfinance...")
        earnings = pull_yfinance_earnings()

    if not earnings.empty:
        out_path = OUTPUT_DIR / "earnings_calendar.csv"
        earnings.to_csv(out_path, index=False)
        print(f"Saved {len(earnings)} earnings records to {out_path}")
        print(earnings.head())
    else:
        print("No earnings data retrieved.")
