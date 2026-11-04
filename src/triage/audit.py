"""Append-only JSONL audit log."""
import json
import os
import time
from pathlib import Path

LOG_PATH = Path(os.getenv("TRIAGE_AUDIT_LOG", "audit.jsonl"))


def log(incident_id: str, step: str, detail: dict, path: Path | None = None) -> None:
    entry = {"ts": time.time(), "incident_id": incident_id, "step": step, "detail": detail}
    with open(path or LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
