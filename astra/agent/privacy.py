from __future__ import annotations

import re


REDACTIONS = [
    # Simple patterns for demo purposes; can be extended with more robust PII detection
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"), "[CARD]"),
    (re.compile(r"\b(?:pass(word)?|pwd)\b[:=]?\s*\S+", re.I), "[PASSWORD]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I), "[EMAIL]"),
]


def scrub_text(text: str) -> str:
    cleaned = text
    for pattern, token in REDACTIONS:
        cleaned = pattern.sub(token, cleaned)
    return cleaned
