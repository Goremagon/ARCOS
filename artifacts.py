import json
import os
import hashlib
import datetime
from typing import Any, Dict

WORKSPACE_ROOT = os.environ.get("ARCOS_WORKSPACE", "workspace")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _timestamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def write_artifact(category: str, payload: Dict[str, Any], prefix: str) -> str:
    category_path = os.path.join(WORKSPACE_ROOT, category)
    _ensure_dir(category_path)
    filename = f"{prefix}_{_timestamp()}.json"
    path = os.path.join(category_path, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return path


def compute_sha256(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def latest_artifact_path(category: str) -> str | None:
    category_path = os.path.join(WORKSPACE_ROOT, category)
    if not os.path.isdir(category_path):
        return None
    files = [f for f in os.listdir(category_path) if f.endswith(".json")]
    if not files:
        return None
    files.sort()
    return os.path.join(category_path, files[-1])
