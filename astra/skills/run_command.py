from __future__ import annotations

import shlex
from typing import List

from ..agent.executor import WHITELIST


def build_run_command_plan(cmd: str) -> List[str]:
    parts = shlex.split(cmd)
    if not parts:
        raise ValueError("Empty command")

    binary = parts[0]
    if binary not in WHITELIST["commands"]:
        raise ValueError(f"Command '{binary}' not allowed (whitelist).")

    # Limit args length and block globbing injection
    safe_parts = []
    for p in parts:
        if len(p) > 256:
            raise ValueError("Argument too long")
        safe_parts.append(p)

    return [" ".join(shlex.quote(p) for p in safe_parts)]
