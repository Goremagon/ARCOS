import sqlite3
import os
import datetime
import time

# CRITICAL FIX: Use Absolute Docker Path
# The Dockerfile sets WORKDIR to /app, and we mount to /app/workspace
DB_FILE = "/app/workspace/arcos_vault.db"

def init_db():
    """Creates the vault in Standard Mode."""
    # Ensure the directory exists inside the container
    db_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    conn = sqlite3.connect(DB_FILE, timeout=30)
    c = conn.cursor()
    
    # Create the Master Ledger table
    c.execute('''CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ticker TEXT,
        signal TEXT,
        price_close REAL,
        sentiment_score REAL,
        raw_ml_prob REAL,
        final_prob REAL,
        rationale TEXT
    )''')
    
    conn.commit()
    conn.close()
    print(f"   🗄️ [Vault] Database initialized at {DB_FILE}")

def log_decision(ticker, signal, price, sentiment, raw_prob, final_prob, rationale):
    """Saves a decision to the vault."""
    attempts = 0
    while attempts < 3:
        try:
            conn = sqlite3.connect(DB_FILE, timeout=30)
            c = conn.cursor()
            
            timestamp = datetime.datetime.now().isoformat()
            
            c.execute('''INSERT INTO signals 
                         (timestamp, ticker, signal, price_close, sentiment_score, raw_ml_prob, final_prob, rationale)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                      (timestamp, ticker, signal, price, sentiment, raw_prob, final_prob, rationale))
            
            conn.commit()
            conn.close()
            print(f"   🔐 [Vault] Saved {ticker} decision to history.")
            return
        except sqlite3.OperationalError:
            attempts += 1
            time.sleep(1)
            print(f"   ⚠️ [Vault] DB Locked, retrying ({attempts}/3)...")
        except Exception as e:
            print(f"   ❌ [Vault] Write Error: {e}")
            return

def get_history(ticker=None, limit=50):
    """Retrieves past data for the dashboard."""
    if not os.path.exists(DB_FILE):
        return []
        
    try:
        conn = sqlite3.connect(DB_FILE, timeout=30)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if ticker:
            c.execute("SELECT * FROM signals WHERE ticker=? ORDER BY id DESC LIMIT ?", (ticker, limit))
        else:
            c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,))
        
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        return []