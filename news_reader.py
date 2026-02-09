import datetime
from typing import Dict, List

from artifacts import write_artifact

HARD_FLAGS = ["fraud", "investigation", "regulatory", "guidance cut", "layoffs"]


def score_headlines(ticker: str, headlines: List[str]) -> Dict:
    scored = []
    for title in headlines:
        lowered = title.lower()
        flags = [flag for flag in HARD_FLAGS if flag in lowered]
        scored.append({
            "title": title,
            "flags": flags,
            "sentiment": 0.0,
            "confidence": 0.0,
        })

    payload = {
        "type": "NewsImpactReport",
        "ticker": ticker,
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "articles": scored,
        "hard_flags": sorted({flag for item in scored for flag in item["flags"]}),
        "recency_weighted": True,
    }
    path = write_artifact("news", payload, f"news_{ticker}")
    return {"payload": payload, "path": path}
