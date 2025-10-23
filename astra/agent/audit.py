from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from .config import config


def _ensure_key(path: Path) -> bytes:
    if not path.exists():
        key = Fernet.generate_key()
        path.write_bytes(key)
        return key
    return path.read_bytes()


class SecureAuditLog:
    def __init__(self, dir_path: Path, key_file: Path):
        self.dir = dir_path
        self.dir.mkdir(parents=True, exist_ok=True)
        key = _ensure_key(key_file)
        self.fernet = Fernet(key)

    def write(self, record: dict[str, Any]) -> None:
        ts = int(time.time() * 1000)
        data = json.dumps(record, ensure_ascii=False).encode("utf-8")
        token = self.fernet.encrypt(data)
        (self.dir / f"event_{ts}.log").write_bytes(token)


audit = SecureAuditLog(config.audit_dir, config.audit_key_file)
