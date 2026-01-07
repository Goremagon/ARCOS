import requests
import random
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- CONFIGURATION ---
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

SUBREDDITS = {
    "AAPL": "https://www.reddit.com/r/stocks/search.json?q=AAPL&sort=new&restrict_sr=1",
    "TSLA": "https://www.reddit.com/r/wallstreetbets/search.json?q=TSLA&sort=new&restrict_sr=1",
    "NVDA": "https://www.reddit.com/r/investing/search.json?q=NVDA&sort=new&restrict_sr=1",
    "GME": "https://www.reddit.com/r/Superstonk/search.json?q=GME&sort=new&restrict_sr=1",
    "BTC-USD": "https://www.reddit.com/r/Bitcoin/search.json?q=Bitcoin&sort=new&restrict_sr=1",
    "SPY": "https://www.reddit.com/r/stocks/search.json?q=SPY&sort=new&restrict_sr=1"
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
]

def analyze_with_llm(text):
    """
    Sends text to your local RTX 3090 (Ollama) for deep analysis.
    Returns a score from -1.0 to 1.0.
    """
    prompt = f"""
    Analyze the sentiment of this stock market headline: "{text}"
    Reply with ONLY a number between -1.0 (Bearish/Negative) and 1.0 (Bullish/Positive).
    0.0 is neutral. Do not write any words, just the number.
    """
    
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }
        # Send to the Windows Host
        response = requests.post(OLLAMA_URL, json=payload, timeout=5)
        
        if response.status_code == 200:
            result_text = response.json().get("response", "").strip()
            # Try to parse the number
            try:
                score = float(result_text)
                return max(-1.0, min(1.0, score)) # Clamp between -1 and 1
            except ValueError:
                return 0.0 # LLM talked too much, treat as neutral
        else:
            return None # LLM Failed
            
    except Exception:
        return None # Connection Failed (Ollama likely off)

def get_reddit_sentiment(ticker):
    """
    Hybrid Scraper: Tries LLM first, falls back to VADER if LLM is offline.
    """
    url = SUBREDDITS.get(ticker)
    if not url:
        url = f"https://www.reddit.com/r/stocks/search.json?q={ticker}&sort=new&restrict_sr=1"

    # print(f"   👽 [Social] Scouting Reddit (JSON) for {ticker}...")
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return 0.0, 0

        data = response.json()
        posts = data.get("data", {}).get("children", [])
        
        if not posts:
            return 0.0, 0

        # Fallback Brain
        vader = SentimentIntensityAnalyzer()
        
        scores = []
        llm_used = False
        
        # Analyze top 5 posts (LLM is heavy, don't do 20)
        for post in posts[:5]:
            title = post["data"].get("title", "")
            if title:
                # 1. Try RTX 3090 Analysis
                score = analyze_with_llm(title)
                
                # 2. Fallback to VADER if Ollama fails
                if score is None:
                    score = vader.polarity_scores(title)['compound']
                else:
                    llm_used = True
                    
                scores.append(score)
        
        avg_sentiment = sum(scores) / len(scores) if scores else 0.0
        volume = len(scores)
        
        # Log the top headline so we see it working
        if posts:
            top_title = posts[0]["data"].get("title", "N/A")
            source = "LLM (Llama 3.2)" if llm_used else "VADER (Backup)"
            print(f"   🧠 [Neural] Analyzed: '{top_title[:50]}...' using {source}")
            
        return avg_sentiment, volume

    except Exception as e:
        print(f"   ❌ [Social] Error: {e}")
        return 0.0, 0