import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
import warnings

# --- CONFIGURATION ---
warnings.simplefilter(action='ignore', category=FutureWarning)
TICKER = "SPY"
START_DATE = "2007-01-01" 
INITIAL_CAPITAL = 10000.0
TRAINING_WINDOW = 500

def prepare_data(df):
    df = df.copy()
    df['Returns'] = df['Close'].pct_change()
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['Trend'] = np.where(df['SMA_5'] > df['SMA_20'], 1, 0)
    df['Vol'] = df['Returns'].rolling(window=5).std()
    df.dropna(inplace=True)
    return df

def calculate_max_drawdown(value_history):
    """Calculates the worst peak-to-valley drop in %."""
    series = pd.Series(value_history)
    running_max = series.cummax()
    drawdown = (series - running_max) / running_max
    return drawdown.min() * 100

def run_backtest():
    print(f"-------- ARCOS RISK AUDIT: {TICKER} --------")
    print(f"Simulating {START_DATE} to Today...")
    
    full_data = yf.download(TICKER, start="2005-01-01", progress=False)
    try:
        start_index = full_data.index.get_loc(START_DATE)
    except:
        start_index = full_data.index.searchsorted(START_DATE)

    cash = INITIAL_CAPITAL
    shares = 0
    history = []
    
    # Track Benchmark (Buy & Hold) Daily Value for comparison
    bh_shares = INITIAL_CAPITAL / float(full_data['Close'].iloc[start_index])
    bh_history = []

    print(f"Processing {len(full_data) - start_index} days...")

    for i in range(start_index, len(full_data) - 1):
        try:
            current_date = full_data.index[i]
            current_price = full_data['Close'].iloc[i].item()
        except:
            current_price = float(full_data['Close'].iloc[i])

        # --- ARCOS LOGIC ---
        window_start = i - TRAINING_WINDOW
        if window_start < 0: continue
        
        visible_data = full_data.iloc[window_start:i+1]
        processed_data = prepare_data(visible_data)
        if len(processed_data) < 50: continue

        X = processed_data[['Trend', 'Vol']]
        y = np.where(processed_data['Returns'].shift(-1) > 0, 1, 0)
        
        model = LogisticRegression()
        model.fit(X[:-1], y[:-1])
        
        probability = model.predict_proba(X.iloc[[-1]])[0][1]
        
        signal = "WAIT"
        if probability > 0.60: signal = "BUY"
        elif probability < 0.40: signal = "SELL"
        
        if signal == "BUY" and cash > current_price:
            shares_to_buy = int(cash // current_price)
            cash -= shares_to_buy * current_price
            shares += shares_to_buy
        elif signal == "SELL" and shares > 0:
            cash += shares * current_price
            shares = 0

        arcos_val = cash + (shares * current_price)
        history.append(arcos_val)
        
        # --- BENCHMARK LOGIC ---
        bh_val = bh_shares * current_price
        bh_history.append(bh_val)
        
        if i % 500 == 0:
            print(f"   📅 {current_date.year}: ARCOS ${arcos_val:,.0f} vs S&P ${bh_val:,.0f}")

    # --- FINAL METRICS ---
    arcos_final = history[-1]
    bh_final = bh_history[-1]
    
    arcos_dd = calculate_max_drawdown(history)
    bh_dd = calculate_max_drawdown(bh_history)
    
    arcos_ret = ((arcos_final - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    bh_ret = ((bh_final - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

    print("\n================ RISK REPORT ================")
    print(f"Metric            ARCOS           S&P 500 (Buy/Hold)")
    print(f"---------------------------------------------")
    print(f"Final Balance:    ${arcos_final:,.0f}         ${bh_final:,.0f}")
    print(f"Total Return:     {arcos_ret:+.1f}%        {bh_ret:+.1f}%")
    print(f"MAX DRAWDOWN:     {arcos_dd:.1f}%          {bh_dd:.1f}%")
    print("=============================================")
    
    if abs(arcos_dd) < abs(bh_dd):
        print(f"🛡️ SAFETY VICTORY: ARCOS reduced crash risk by {abs(bh_dd) - abs(arcos_dd):.1f}%")
        print("   This makes the strategy 'Institutional Grade'.")
    else:
        print("⚠️ ARCOS was riskier than the market.")

if __name__ == "__main__":
    run_backtest()