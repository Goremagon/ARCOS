import pandas as pd
import lstm_brain # <--- NEW IMPORT

def run_simulation(ticker, df, sentiment_score):
    """
    Hybrid Decision Engine: LSTM (Price Patterns) + LLM (Sentiment)
    """
    # 1. Ask the LSTM Brain (0.0 to 1.0)
    try:
        price_prob = lstm_brain.train_and_predict(df)
    except Exception as e:
        print(f"   ⚠️ [Brain] LSTM Error: {e}")
        price_prob = 0.5

    # 2. Fuse with Sentiment
    # Sentiment (-1 to 1) shifts probability by up to 20%
    sentiment_impact = sentiment_score * 0.20
    final_prob = price_prob + sentiment_impact
    
    # 3. Generate Signal
    signal = "WAIT"
    rationale = f"LSTM predicted {price_prob:.2f}. Sentiment ({sentiment_score:.2f}) adjusted it to {final_prob:.2f}."
    
    if final_prob > 0.70: # Higher threshold for LSTM
        signal = "BUY_CANDIDATE"
    elif final_prob < 0.30:
        signal = "SELL_AVOID"
        
    return {
        "ticker": ticker,
        "signal": signal,
        "prob": final_prob,
        "uncertainty": 0.0,
        "sample_size": len(df),
        "rationale": rationale
    }