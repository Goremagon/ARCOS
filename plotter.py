import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt
import warnings

# Silence warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Config
TICKER = "SPY"
START_DATE = "2007-01-01"
TRAINING_WINDOW = 500

def run_plot():
    print("🎨 Generating Institutional Performance Chart...")
    
    # 1. Fetch Data
    full_data = yf.download(TICKER, start="2005-01-01", progress=False)
    
    # Data Prep Logic (Same as backtester)
    df = full_data.copy()
    df['Returns'] = df['Close'].pct_change()
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['Trend'] = np.where(df['SMA_5'] > df['SMA_20'], 1, 0)
    df['Vol'] = df['Returns'].rolling(window=5).std()
    df.dropna(inplace=True)

    try:
        start_index = df.index.get_loc(START_DATE)
    except:
        start_index = df.index.searchsorted(START_DATE)

    # 2. Run Fast Simulation
    arcos_curve = [100.0] # Start at 100% (Normalized)
    spy_curve = [100.0]
    dates = [df.index[start_index]]
    
    cash = 10000.0
    shares = 0
    
    # Benchmark
    initial_price = float(df['Close'].iloc[start_index].item())
    bh_shares = 10000.0 / initial_price

    print("   Processing data points...")
    for i in range(start_index, len(df) - 1):
        # Rolling Window Model
        window_start = i - TRAINING_WINDOW
        if window_start < 0: continue
        
        train_data = df.iloc[window_start:i+1]
        
        X = train_data[['Trend', 'Vol']]
        y = np.where(train_data['Returns'].shift(-1) > 0, 1, 0)
        
        model = LogisticRegression()
        model.fit(X[:-1], y[:-1])
        
        prob = model.predict_proba(X.iloc[[-1]])[0][1]
        current_price = float(df['Close'].iloc[i].item())
        
        # Strategy
        if prob > 0.60 and cash > current_price:
            shares_buy = int(cash // current_price)
            cash -= shares_buy * current_price
            shares += shares_buy
        elif prob < 0.40 and shares > 0:
            cash += shares * current_price
            shares = 0
            
        # Record Daily Values
        arcos_val = cash + (shares * current_price)
        spy_val = bh_shares * current_price
        
        # Normalize to percentage start (100)
        arcos_curve.append((arcos_val / 10000.0) * 100)
        spy_curve.append((spy_val / 10000.0) * 100)
        dates.append(df.index[i])

    # 3. Plotting
    plt.figure(figsize=(12, 6))
    plt.style.use('dark_background') # The "Terminal" Look
    
    plt.plot(dates, arcos_curve, label='ARCOS AI', color='#00ff00', linewidth=1.5)
    plt.plot(dates, spy_curve, label='S&P 500 (Buy & Hold)', color='#888888', linewidth=1, alpha=0.7)
    
    plt.title(f"ARCOS vs WALL STREET ({START_DATE} - Present)", fontsize=14, color='white')
    plt.ylabel("Portfolio Growth (%)", color='white')
    plt.legend()
    plt.grid(color='#333333', linestyle='--', linewidth=0.5)
    
    # Save
    output_path = "workspace/performance_chart.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Chart saved to: {output_path}")

if __name__ == "__main__":
    run_plot()