"""Rule-based first-pass classifier. Cheap, deterministic, explainable."""
import re

RULES = {
    "auth_failure": [
        r"auth", r"credential", r"permission denied", r"401", r"403", r"token expired",
    ],
    "storage_full": [r"no space", r"quota", r"capacity", r"disk full", r"storage threshold"],
    "agent_unreachable": [
        r"unreachable", r"connection refused", r"agent", r"host down", r"timed out connecting",
    ],
    "snapshot_timeout": [r"snapshot", r"timeout", r"took longer", r"exceeded window"],
}


def classify(message: str) -> tuple[str, float]:
    text = message.lower()
    scores = {
        cat: sum(1 for p in pats if re.search(p, text)) for cat, pats in RULES.items()
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "unknown", 0.0
    total = sum(scores.values())
    return best, round(scores[best] / total, 2)
