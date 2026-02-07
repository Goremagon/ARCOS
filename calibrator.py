import datetime
import os
import sqlite3
from typing import Dict

from artifacts import write_artifact

DB_FILE = os.environ.get("ARCOS_DB_PATH", "/app/workspace/arcos_vault.db")


def compute_calibration() -> Dict:
    if not os.path.exists(DB_FILE):
        return {
            "type": "CalibrationState",
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "signal_stats": {},
            "drift_alerts": [],
        }

    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT signal, final_prob FROM signals").fetchall()
    conn.close()

    stats = {}
    for row in rows:
        stats.setdefault(row["signal"], []).append(row["final_prob"])

    signal_stats = {
        signal: {
            "count": len(values),
            "avg_confidence": float(sum(values) / len(values)) if values else 0.0,
        }
        for signal, values in stats.items()
    }

    drift_alerts = [
        {
            "signal": signal,
            "issue": "low_confidence",
            "avg_confidence": meta["avg_confidence"],
        }
        for signal, meta in signal_stats.items()
        if meta["avg_confidence"] < 0.5
    ]

    payload = {
        "type": "CalibrationState",
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "signal_stats": signal_stats,
        "drift_alerts": drift_alerts,
    }
    write_artifact("calibration", payload, "calibration_state")

    drift_payload = {
        "type": "DriftAlerts",
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "alerts": drift_alerts,
    }
    write_artifact("calibration", drift_payload, "drift_alerts")
    return payload


if __name__ == "__main__":
    compute_calibration()
