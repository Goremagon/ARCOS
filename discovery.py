import requests
import re

def get_trending_tickers():
    """
    Scrapes Yahoo Finance 'Trending' and 'Most Active' to find targets.
    Returns a list of tickers (e.g., ['NVDA', 'TSLA', 'AMD']).
    """
    targets = set()
    
    # 1. Yahoo Finance Trending (JSON API)
    # This endpoint is often used by their frontend
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/trending/US"
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=5)
        data = resp.json()
        
        quotes = data['finance']['result'][0]['quotes']
        for q in quotes:
            symbol = q['symbol']
            # Filter out weird stuff (Rights, Warrants)
            if len(symbol) <= 5 and symbol.isalpha():
                targets.add(symbol)
                
        print(f"   🔭 [Discovery] Found Trending: {list(targets)}")
    except Exception as e:
        print(f"   ⚠️ [Discovery] Yahoo Trending failed: {e}")

    # 2. Hardcoded 'Always Watch' list (Blue Chips + Crypto)
    always_watch = ["SPY", "QQQ", "BTC-USD", "ETH-USD", "NVDA", "TSLA", "AMD", "GME"]
    targets.update(always_watch)
    
    return list(targets)

if __name__ == "__main__":
    print(get_trending_tickers())