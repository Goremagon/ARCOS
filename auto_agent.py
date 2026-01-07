import time
import datetime
import random
import os
import html
import data_fetcher
import signal_engine
import social_scraper 
import db_manager
import discovery

# --- CONFIGURATION ---
REPORT_INTERVAL = 3600  # Send summary every 60 minutes
MIN_BATCH_SIZE = 1      

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
    print("   ARCOS GRANDMASTER: v3.5 (Batched)")
    print("---------------------------------------")

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
                active_watchlist = discovery.get_trending_tickers()
                last_scan_time = time.time()
                print(f"   🎯 [System] Tracking {len(active_watchlist)} Assets")

            ticker = random.choice(active_watchlist)
            
            # 2. Fetch Data
            df = data_fetcher.fetch_history(ticker)
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
                
                message_id = f"SIG-{random.randint(10000, 99999)}"
                timestamp = datetime.datetime.now().isoformat()
                xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<ArcosMessage>
    <Header>
        <MessageID>{message_id}</MessageID>
        <Sender>HUNTER_KILLER_URGENT</Sender>
        <Timestamp>{timestamp}</Timestamp>
    </Header>
    <Body>
        <Ticker>{ticker}</Ticker>
        <Signal>URGENT_{tag}</Signal>
        <Probability>{result['prob']}</Probability>
        <Uncertainty>0.0</Uncertainty>
        <SampleSize>0</SampleSize>
        <Rationale>IMMEDIATE VOLATILITY: {percent_change:+.2f}%</Rationale>
        <Signature>ARCOS_v3.5</Signature>
    </Body>
</ArcosMessage>
"""
                with open(f"workspace/temp_{message_id}.xml", "w", encoding="utf-8") as f:
                    f.write(xml_data)
                os.replace(f"workspace/temp_{message_id}.xml", f"workspace/message_{message_id}.xml")
                panic_cooldowns[ticker] = time.time()

            # B. Standard Buy (Buffered - The Digest)
            # We DO NOT generate XML here. We just save it to memory.
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
                safe_summary = html.escape(summary_text)
                
                message_id = f"RPT-{random.randint(10000, 99999)}"
                timestamp = datetime.datetime.now().isoformat()
                
                xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<ArcosMessage>
    <Header>
        <MessageID>{message_id}</MessageID>
        <Sender>ARCOS_BRIEFING</Sender>
        <Timestamp>{timestamp}</Timestamp>
    </Header>
    <Body>
        <Ticker>MARKET_BRIEF</Ticker>
        <Signal>INFO</Signal>
        <Probability>1.0</Probability>
        <Uncertainty>0.0</Uncertainty>
        <SampleSize>{len(pending_reports)}</SampleSize>
        <Rationale>{safe_summary}</Rationale>
        <Signature>ARCOS_v3.5</Signature>
    </Body>
</ArcosMessage>
"""
                with open(f"workspace/temp_{message_id}.xml", "w", encoding="utf-8") as f:
                    f.write(xml_data)
                os.replace(f"workspace/temp_{message_id}.xml", f"workspace/message_{message_id}.xml")
                
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