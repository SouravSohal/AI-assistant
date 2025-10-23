from __future__ import annotations

import re


def estimate_token_count(text: str) -> int:
    # very rough heuristic: ~0.75 tokens per word
    words = len(text.split())
    return int(words * 0.75)


def is_privacy_sensitive(text: str) -> bool:
    # basic PII patterns
    patterns = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN-like
        r"\b\d{16}\b",  # credit-card-like
        r"\bpassword\b",
    ]
    return any(re.search(p, text, re.I) for p in patterns)


def intent_is_system_action(text: str) -> bool:
    return bool(re.search(r"\b(open|launch|start|systemctl|service|run|execute)\b", text, re.I))


def requires_confirmation(cmd: str) -> bool:
    risky = [
        r"\brm\s+-rf\b",
        r"\bdd\b",
        r"\bmkfs\b",
        r"\bparted\b",
        r"\bsudo\b",
        r"\bchown\b\s+/.+",
    ]
    return any(re.search(p, cmd) for p in risky)
