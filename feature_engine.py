import datetime
from typing import Dict
import pandas as pd

from artifacts import write_artifact


def compute_features(ticker: str, df: pd.DataFrame) -> Dict:
    df = df.copy()
    df['return'] = df['Close'].pct_change()
    df['sma_20'] = df['Close'].rolling(20).mean()
    df['sma_50'] = df['Close'].rolling(50).mean()
    df['volatility_20'] = df['return'].rolling(20).std()
    df.dropna(inplace=True)

    if df.empty:
        features = {}
    else:
        latest = df.iloc[-1]
        features = {
            "momentum": float(latest['return']),
            "trend_alignment": float((latest['sma_20'] - latest['sma_50']) / latest['sma_50']),
            "volatility_regime": float(latest['volatility_20']),
        }

    payload = {
        "type": "FeatureStore",
        "ticker": ticker,
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "features": features,
        "window": {
            "sma_short": 20,
            "sma_long": 50,
            "vol_window": 20,
        },
    }
    path = write_artifact("features", payload, f"features_{ticker}")
    return {"payload": payload, "path": path}
