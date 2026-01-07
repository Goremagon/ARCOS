import yfinance as yf
import pandas as pd
import datetime
import time

def fetch_history(ticker):
    """
    Fetches market data with intelligent fallback.
    Mode 1: High-Frequency (15m) for active trading.
    Mode 2: Daily (1d) fallback for crypto/long-term trends.
    """
    # 1. Try High-Frequency (The Hunter Strategy)
    try:
        # We grab 5 days of 15-minute candles. 
        # This is the "sweet spot" for short-term momentum.
        df = yf.download(ticker, period="5d", interval="15m", progress=False)
        
        # Validation: Do we have enough data to calculate a trend?
        if not df.empty and len(df) > 20:
            return df
            
    except Exception as e:
        print(f"   ⚠️ [Data] 15m fetch failed for {ticker}: {e}")

    # 2. Fallback to Daily (The Sniper Strategy)
    # If 15m fails (common with some crypto or indices), grab standard daily data
    try:
        # print(f"   🔄 [Data] Falling back to daily data for {ticker}...")
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        return df
    except Exception as e:
        print(f"   ❌ [Data] Critical Failure for {ticker}: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Quick test to prove it works
    print("Testing Data Fetcher...")
    test_df = fetch_history("NVDA")
    print(f"Received {len(test_df)} rows of data.")