import yfinance as yf
import pandas as pd
import datetime
import time
from typing import Dict, List

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


def fetch_fundamentals(ticker: str) -> Dict:
    """
    Fetches basic fundamentals where available.
    """
    try:
        info = yf.Ticker(ticker).info
        return {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "profit_margins": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
        }
    except Exception:
        return {}


def fetch_news(ticker: str) -> List[Dict]:
    """
    Fetches recent news metadata from yfinance.
    """
    try:
        news_items = yf.Ticker(ticker).news or []
        return [
            {
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "link": item.get("link"),
                "provider_publish_time": item.get("providerPublishTime"),
            }
            for item in news_items
        ]
    except Exception:
        return []


def fetch_macro_calendar() -> Dict:
    """
    Placeholder for macro calendar.
    """
    return {
        "events": [],
        "source": "placeholder",
    }

if __name__ == "__main__":
    # Quick test to prove it works
    print("Testing Data Fetcher...")
    test_df = fetch_history("NVDA")
    print(f"Received {len(test_df)} rows of data.")
