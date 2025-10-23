from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class CloudAdapter:
    cfg: Any

    def predict(self, prompt: str, context: Dict) -> Dict:
        # Stub; integrate OpenAI later
        if not self.cfg.openai_api_key:
            return {"text": "", "confidence": 0.0, "error": "CLOUD_DISABLED"}
        # Implement OpenAI/Anthropic call here with PII scrubbing before upload
        return {"text": "", "confidence": 0.6}
