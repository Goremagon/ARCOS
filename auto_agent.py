import time
import datetime
import random
import os
import html
import json
import threading
import redis
from http.server import HTTPServer, BaseHTTPRequestHandler
import data_fetcher
import signal_engine
import social_scraper 
import db_manager
import discovery

# --- CONFIGURATION ---
REPORT_INTERVAL = 3600  # Send summary every 60 minutes
MIN_BATCH_SIZE = 1      

# --- REDIS SETUP ---
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    print(f"   🔌 [System] Connected to Redis at {REDIS_URL}")
except Exception as e:
    print(f"   ❌ [System] Redis Connection Error: {e}")
    r = None

# --- HEALTH CHECK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return # Silence logs

def start_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"   ❤️ [System] Health Check running on port {port}")
    server.serve_forever()

def send_signal_to_redis(message_type, ticker, signal, prob, rationale, tags=None):
    if not r:
        print("   ⚠️ [System] Redis unavailable, skipping signal send.")
        return

    payload = {
        "header": {
            "message_id": f"{message_type}-{random.randint(10000, 99999)}",
            "sender": "ARCOS_AGENT",
            "timestamp": datetime.datetime.now().isoformat()
        },
        "body": {
            "ticker": ticker,
            "signal": signal,
            "probability": prob,
            "uncertainty": 0.0,
            "sample_size": 0,
            "rationale": rationale,
            "signature": "ARCOS_v3.5_REDIS",
            "tags": tags or []
        }
    }
    
    try:
        r.rpush("arcos_signals", json.dumps(payload))
        print(f"   🚀 [Redis] Pushed {signal} for {ticker}")
    except Exception as e:
        print(f"   ❌ [Redis] Push Failed: {e}")

def format_batch_report(reports):
    lines = ["🏛️ ARCOS NEURAL BRIEFING", "--------------------------------"]
    for r in reports:
        # E.g. "NVDA: BUY (0.85) | Sentiment: 0.45"
        line = f"• {r['ticker']:<5} {r['signal']} ({r['prob']:.2f}) | {r['note']}"
        lines.append(line)
    lines.append("--------------------------------")
    lines.append(f"Active Targets: {len(reports)}")
    return "\n".join(lines)

def run_bot_loop():
    print("---------------------------------------")
    print("   ARCOS GRANDMASTER: v3.5 (Cloud Native)")
    print("---------------------------------------")

    # Start Health Check in Background
    t = threading.Thread(target=start_health_check, daemon=True)
    t.start()

    db_manager.init_db()
    
    active_watchlist = []
    last_scan_time = 0
    pending_reports = []
    last_report_time = time.time()
    panic_cooldowns = {}

    while True:
        try:
            # 1. Refresh Watchlist (Every 30 mins)
            if time.time() - last_scan_time > 1800 or not active_watchlist:
                print("   🔭 [System] Scanning market for new targets...")
                # Fallback if discovery fails?
                try:
                    active_watchlist = discovery.get_trending_tickers()
                except:
                    active_watchlist = ["AAPL", "TSLA", "NVDA", "AMD"] # Fallback
                last_scan_time = time.time()
                print(f"   🎯 [System] Tracking {len(active_watchlist)} Assets")

            if not active_watchlist:
                time.sleep(5)
                continue

            ticker = random.choice(active_watchlist)
            
            # 2. Fetch Data
            try:
                df = data_fetcher.fetch_history(ticker)
            except:
                continue

            if df.empty or len(df) < 20: 
                continue
            
            current_price = float(df['Close'].iloc[-1].item())
            try:
                prev_price = float(df['Close'].iloc[-2].item())
                percent_change = ((current_price - prev_price) / prev_price) * 100
            except:
                percent_change = 0.0
            
            # 3. Neural Social (RTX 3090)
            try:
                sentiment_score, social_vol = social_scraper.get_reddit_sentiment(ticker)
            except:
                sentiment_score, social_vol = 0.0, 0
            
            # 4. Brain Analysis (LSTM + Logic)
            result = signal_engine.run_simulation(ticker, df, sentiment_score)
            
            # 5. Log to Vault
            social_note = f"Sent:{sentiment_score:.2f}"
            raw_rationale = result['rationale'] + " | " + social_note
            if abs(percent_change) > 2.0: raw_rationale += f" [VOLATILITY: {percent_change:+.2f}%]"
            
            safe_rationale = html.escape(raw_rationale)
            
            db_manager.log_decision(
                ticker=ticker,
                signal=result['signal'],
                price=current_price,
                sentiment=sentiment_score,
                raw_prob=0.0,
                final_prob=result['prob'],
                rationale=raw_rationale
            )

            print(f"   💾 [Hunter] {ticker}: {result['signal']} ({result['prob']:.2f}) | {percent_change:+.2f}%")

            # 6. HYBRID ALERTING (Anti-Spam)
            
            # A. Panic (Immediate - The Circuit Breaker)
            # Only email instantly if price crashes/pumps > 3% AND we haven't emailed in 10 mins
            is_crash = percent_change < -3.0
            is_pump = percent_change > 3.0
            
            if (is_crash or is_pump) and (time.time() - panic_cooldowns.get(ticker, 0) > 600):
                tag = "CRASH" if is_crash else "MOON"
                print(f"   🚨 [URGENT] Sending Immediate Alert for {ticker} ({tag})")
                
                send_signal_to_redis(
                    message_type="SIG",
                    ticker=ticker,
                    signal=f"URGENT_{tag}",
                    prob=result['prob'],
                    rationale=f"IMMEDIATE VOLATILITY: {percent_change:+.2f}%"
                )
                panic_cooldowns[ticker] = time.time()

            # B. Standard Buy (Buffered - The Digest)
            elif result['signal'] == "BUY_CANDIDATE":
                report_entry = {
                    "ticker": ticker,
                    "signal": "BUY",
                    "prob": result['prob'],
                    "note": f"{percent_change:+.1f}% | {social_note}"
                }
                pending_reports.append(report_entry)
                print(f"   📝 [Batch] Added {ticker} to hourly report ({len(pending_reports)} pending)")

            # 7. Check Batch Timer (Hourly Email)
            if (time.time() - last_report_time > REPORT_INTERVAL) and (len(pending_reports) >= MIN_BATCH_SIZE):
                print("   📧 [System] Compiling Hourly Briefing...")
                summary_text = format_batch_report(pending_reports)
                
                send_signal_to_redis(
                    message_type="RPT",
                    ticker="MARKET_BRIEF",
                    signal="INFO",
                    prob=1.0,
                    rationale=summary_text,
                    tags=["BATCH"]
                )
                
                pending_reports = []
                last_report_time = time.time()
                print("   ✅ [System] Briefing Sent!")

            # 8. Speed Control
            # Wait 3 seconds to let the 3090 cool down slightly between LSTM training runs
            time.sleep(3) 

        except Exception as e:
            print(f"❌ [Error] Loop failed: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_bot_loop()