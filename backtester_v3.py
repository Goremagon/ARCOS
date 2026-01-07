import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

# --- HUNTER CONFIGURATION ---
TICKER = "NVDA"  # Test a volatile stock suited for Hunter logic
PERIOD = "60d"   # Max available for 15m data
INTERVAL = "15m"
INITIAL_CAPITAL = 10000.0
TRAINING_WINDOW = 100 # 100 candles = approx 3 days of trading history

def prepare_data(df):
    df = df.copy()
    df['Returns'] = df['Close'].pct_change()
    df['SMA_5'] = df['Close'].rolling(window=5).mean()   # Fast Moving Average
    df['SMA_20'] = df['Close'].rolling(window=20).mean() # Slow Moving Average
    df['Trend'] = np.where(df['SMA_5'] > df['SMA_20'], 1, 0)
    df['Vol'] = df['Returns'].rolling(window=5).std()
    df.dropna(inplace=True)
    return df

def run_short_test():
    print(f"-------- ARCOS V3 SHORT-RANGE TEST: {TICKER} --------")
    print(f"Simulating High-Frequency (15m) Trading over last 60 days...")
    
    # 1. Fetch High-Res Data
    print("Downloading 15-minute candles...")
    full_data = yf.download(TICKER, period=PERIOD, interval=INTERVAL, progress=False)
    
    if len(full_data) < 200:
        print("❌ Not enough intraday data.")
        return

    cash = INITIAL_CAPITAL
    shares = 0
    history = []
    
    # Benchmark
    try:
        start_price = full_data['Close'].iloc[TRAINING_WINDOW].item()
    except:
        start_price = float(full_data['Close'].iloc[TRAINING_WINDOW])
        
    bh_shares = INITIAL_CAPITAL / start_price

    print(f"Processing {len(full_data)} candles...")

    # 2. The Intraday Loop
    for i in range(TRAINING_WINDOW, len(full_data) - 1):
        try:
            current_price = full_data['Close'].iloc[i].item()
            current_time = full_data.index[i]
        except:
            current_price = float(full_data['Close'].iloc[i])
            current_time = full_data.index[i]

        # A. Rolling Window (Intraday)
        window_start = i - TRAINING_WINDOW
        visible_data = full_data.iloc[window_start:i+1]
        
        processed_data = prepare_data(visible_data)
        if len(processed_data) < 20: continue

        X = processed_data[['Trend', 'Vol']]
        y = np.where(processed_data['Returns'].shift(-1) > 0, 1, 0)
        
        # B. Train on recent intraday moves
        try:
            model = LogisticRegression()
            model.fit(X[:-1], y[:-1])
            probability = model.predict_proba(X.iloc[[-1]])[0][1]
        except:
            continue
        
        # C. Signal (Aggressive Hunter Logic)
        # Note: We cannot simulate 'Neural Sentiment' historically, 
        # so we test the Pure Price Action of v3.0
        signal = "WAIT"
        if probability > 0.65: signal = "BUY" # Higher threshold as per v3 code
        elif probability < 0.40: signal = "SELL"
        
        # D. Execute
        if signal == "BUY" and cash > current_price:
            shares_to_buy = int(cash // current_price)
            cash -= shares_to_buy * current_price
            shares += shares_to_buy
        elif signal == "SELL" and shares > 0:
            cash += shares * current_price
            shares = 0

        # Track Value
        total_val = cash + (shares * current_price)
        history.append(total_val)

    # 3. Results
    final_val = history[-1]
    
    try:
        end_price = full_data['Close'].iloc[-1].item()
    except:
        end_price = float(full_data['Close'].iloc[-1])
        
    bh_val = bh_shares * end_price
    
    arcos_ret = ((final_val - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    bh_ret = ((bh_val - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

    print("\n================ 60-DAY HUNTER REPORT ================")
    print(f"Strategy:        15-Minute Candles (No Sentiment)")
    print(f"ARCOS Final:     ${final_val:,.2f} ({arcos_ret:+.2f}%)")
    print(f"Buy & Hold:      ${bh_val:,.2f} ({bh_ret:+.2f}%)")
    print("======================================================")
    
    if final_val > bh_val:
        print("🚀 Hunter Logic beats the market on short timeframes!")
    else:
        print("📉 Volatility ate the profits. Needs Sentiment to filter noise.")

if __name__ == "__main__":
    run_short_test()