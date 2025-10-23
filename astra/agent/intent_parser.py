from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from .config import config
from ..models.local_mistral_adapter import LocalAdapter
from .utils import extract_json_object
from .executor import WHITELIST


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
    # heuristic: single known app name like "firefox"
    tokens = re.findall(r"[a-z0-9\-_.]+", s.lower())
    if len(tokens) == 1 and tokens[0] in WHITELIST.get("apps", set()):
        return Intent("open_app", {"app": tokens[0]}, confidence=0.7)
    return None


def llm_parse_intent(text: str) -> Optional[Intent]:
    """Use local Ollama (Mistral) to extract intent and entities as JSON.

    The model must return ONLY a JSON object of the form:
    {
      "intent": "open_app|run_command|manage_service|none",
      "entities": {"app": "", "cmd": "", "action": "", "service": ""},
      "confidence": 0.0-1.0,
      "reason": "..."
    }
    """
    system = (
        "You are an intent extractor for a Linux desktop assistant."
        " Output only JSON with keys: intent, entities, confidence, reason."
        " allowed intents: open_app, run_command, manage_service, none."
        " entities can include: app, cmd, action, service."
        " Confidence is 0.0 to 1.0. No extra commentary."
    )
    user = f"Text: {text.strip()}"

    adapter = LocalAdapter(config)
    out = adapter.predict(
        user,
        {
            "system_prompt_override": system,
            "gen_options_override": {"temperature": 0.1},
        },
    )
    raw = out.get("text", "").strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        obj = extract_json_object(raw)
        if obj is None:
            return None

    intent_name = (obj.get("intent") or "").strip().lower()
    if intent_name not in {"open_app", "run_command", "manage_service"}:
        return None
    entities = obj.get("entities") or {}
    try:
        conf = float(obj.get("confidence", 0.0))
    except Exception:
        conf = 0.0
    if conf < 0.45:
        return None
    return Intent(name=intent_name, entities=entities, confidence=conf)
