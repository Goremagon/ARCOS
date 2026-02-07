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
import feature_engine
import news_reader
import calibrator
from artifacts import write_artifact

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

def send_signal_to_redis(message_type, ticker, signal, prob, rationale, sample_size=0, win_rate=0.0, tags=None):
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
            "win_rate": win_rate,
            "uncertainty": 0.0,
            "sample_size": sample_size,
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

            fundamentals = data_fetcher.fetch_fundamentals(ticker)
            news_items = data_fetcher.fetch_news(ticker)
            macro_snapshot = data_fetcher.fetch_macro_calendar()

            market_snapshot = {
                "type": "MarketSnapshot",
                "ticker": ticker,
                "as_of": datetime.datetime.utcnow().isoformat(),
                "ohlcv": df.tail(200).to_dict(orient="records"),
                "source": "yfinance",
            }
            market_path = write_artifact("raw", market_snapshot, f"market_{ticker}")

            fundamental_snapshot = {
                "type": "FundamentalSnapshot",
                "ticker": ticker,
                "as_of": datetime.datetime.utcnow().isoformat(),
                "fundamentals": fundamentals,
                "source": "yfinance",
            }
            fundamental_path = write_artifact("raw", fundamental_snapshot, f"fundamentals_{ticker}")

            news_snapshot = {
                "type": "NewsSnapshot",
                "ticker": ticker,
                "as_of": datetime.datetime.utcnow().isoformat(),
                "articles": news_items,
                "source": "yfinance",
            }
            news_path = write_artifact("raw", news_snapshot, f"news_{ticker}")

            macro_path = write_artifact("raw", {
                "type": "MacroSnapshot",
                "as_of": datetime.datetime.utcnow().isoformat(),
                "macro": macro_snapshot,
            }, "macro")

            flow_snapshot = {
                "type": "FlowSnapshot",
                "ticker": ticker,
                "as_of": datetime.datetime.utcnow().isoformat(),
                "flows": [],
                "source": "placeholder",
            }
            flow_path = write_artifact("raw", flow_snapshot, f"flows_{ticker}")

            feature_output = feature_engine.compute_features(ticker, df)
            news_output = news_reader.score_headlines(
                ticker, [item.get("title", "") for item in news_items if item.get("title")]
            )
            
            # 4. Brain Analysis (LSTM + Logic)
            result = signal_engine.run_simulation(ticker, df, sentiment_score)
            signal_candidates = {
                "type": "SignalCandidates",
                "ticker": ticker,
                "generated_at": datetime.datetime.utcnow().isoformat(),
                "candidates": [result],
            }
            signal_path = write_artifact("signals", signal_candidates, f"signals_{ticker}")
            
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
                    rationale=f"IMMEDIATE VOLATILITY: {percent_change:+.2f}%",
                    sample_size=result['sample_size'],
                    win_rate=result['win_rate'],
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

                send_signal_to_redis(
                    message_type="SIG",
                    ticker=ticker,
                    signal="BUY_CANDIDATE",
                    prob=result['prob'],
                    rationale=raw_rationale,
                    sample_size=result['sample_size'],
                    win_rate=result['win_rate'],
                )

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
                    sample_size=len(pending_reports),
                    win_rate=1.0,
                    tags=["BATCH"]
                )
                
                pending_reports = []
                last_report_time = time.time()
                print("   ✅ [System] Briefing Sent!")

            # 8. Speed Control
            # Wait 3 seconds to let the 3090 cool down slightly between LSTM training runs
            time.sleep(3) 

            calibrator.compute_calibration()

        except Exception as e:
            print(f"❌ [Error] Loop failed: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_bot_loop()
