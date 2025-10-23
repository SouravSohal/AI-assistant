from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

import requests


@dataclass
class LocalAdapter:
    cfg: Any

    def predict(self, prompt: str, context: Dict) -> Dict:
        """Call Ollama /api/chat with a system prompt and user prompt.

        Returns a dict with keys: text, confidence, error (optional).
        """
        url = f"{self.cfg.ollama_url}/api/chat"
        # Allow overrides via context
        system_prompt = context.get("system_prompt_override", self.cfg.local_system_prompt)
        options_override = context.get("gen_options_override", {})
        body = {
            "model": self.cfg.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.cfg.ollama_temperature,
                "top_p": self.cfg.ollama_top_p,
                "repeat_penalty": self.cfg.ollama_repeat_penalty,
            },
        }
        # Merge option overrides
        body["options"].update({k: v for k, v in options_override.items() if v is not None})
        try:
            resp = requests.post(url, json=body, timeout=self.cfg.http_timeout_sec)
            if not resp.ok:
                return {"text": "", "confidence": 0.0, "error": f"HTTP {resp.status_code}"}
            data = resp.json()
            # Ollama chat returns {"message": {"content": "..."}} or {"messages": [...]} depending on version
            text = ""
            if isinstance(data, dict):
                if "message" in data and isinstance(data["message"], dict):
                    text = data["message"].get("content", "")
                elif "messages" in data and isinstance(data["messages"], list) and data["messages"]:
                    text = data["messages"][-1].get("content", "")
            return {"text": text or "", "confidence": 0.65}
        except Exception as e:
            return {"text": "", "confidence": 0.0, "error": str(e)}
