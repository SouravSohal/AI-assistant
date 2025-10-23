from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Intent:
    name: str
    entities: dict
    confidence: float


INTENTS = {
    "open_app": [
        re.compile(r"\b(open|launch|start)\s+(?P<app>[a-z0-9\-_. ]+)", re.I),
    ],
    "manage_service": [
        re.compile(
            r"\b(systemctl\s+(?P<action>start|stop|restart|status)\s+(?P<service>[a-z0-9\-_.@]+))",
            re.I,
        ),
        re.compile(
            r"\b(service)\s+(?P<action>start|stop|restart|status)\s+(?P<service>[a-z0-9\-_.@]+)",
            re.I,
        ),
    ],
    "run_command": [
        re.compile(r"\b(run|execute)\s+(?P<cmd>.+)", re.I),
        re.compile(r"^!(?P<cmd>.+)$", re.I),
    ],
}


def parse_intent(text: str) -> Optional[Intent]:
    s = text.strip()
    for name, patterns in INTENTS.items():
        for p in patterns:
            m = p.search(s)
            if m:
                entities = {k: v for k, v in m.groupdict().items() if v}
                return Intent(name=name, entities=entities, confidence=0.78)
    # heuristic: "open firefox"
    m = re.search(r"\bopen\s+(?P<app>[a-z0-9\-_. ]+)", s, re.I)
    if m:
        return Intent("open_app", {"app": m.group("app")}, confidence=0.6)
    return None
