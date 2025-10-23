from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Config:
    app_name: str = "Astra"
    host: str = os.getenv("ASTRA_HOST", "127.0.0.1")
    port: int = int(os.getenv("ASTRA_PORT", "3110"))

    # Routing
    complexity_threshold_tokens: int = int(os.getenv("ASTRA_COMPLEXITY_TOKENS", "800"))
    force_cloud: bool = os.getenv("ASTRA_FORCE_CLOUD", "false").lower() == "true"

    # Privacy
    allow_cloud_uploads: bool = os.getenv("ASTRA_ALLOW_CLOUD", "false").lower() == "true"

    # Security
    enable_firejail: bool = os.getenv("ASTRA_ENABLE_FIREJAIL", "false").lower() == "true"
    confirmations_required: bool = True  # always ask for destructive ops
    run_user: str = os.getenv("USER", "user")

    # Audit
    audit_dir: Path = Path(os.getenv("ASTRA_AUDIT_DIR", BASE_DIR / "data" / "audit"))
    audit_key_file: Path = Path(
        os.getenv("ASTRA_AUDIT_KEY", BASE_DIR / "data" / "audit" / "key.fernet")
    )

    # Models
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "mistral")
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
    ollama_top_p: float = float(os.getenv("OLLAMA_TOP_P", "0.95"))
    ollama_repeat_penalty: float = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1"))
    local_system_prompt: str = os.getenv(
        "ASTRA_LOCAL_SYSTEM_PROMPT",
        "You are Astra, a helpful local assistant on Fedora Linux. Respond concisely and safely.",
    )

    http_timeout_sec: int = int(os.getenv("ASTRA_HTTP_TIMEOUT", "10"))

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")


config = Config()
config.audit_dir.mkdir(parents=True, exist_ok=True)
