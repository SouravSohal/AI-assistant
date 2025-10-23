from __future__ import annotations

import shlex
from typing import List

from ..agent.executor import WHITELIST


def build_manage_service_plan(action: str, service: str) -> List[str]:
    a = action.strip().lower()
    s = service.strip()
    if a not in WHITELIST["service_actions"]:
        raise ValueError("Service action not allowed")
    if s not in WHITELIST["services"]:
        raise ValueError("Service not allowed")
    # Read-only actions only by default
    if a != "status":
        raise PermissionError("Starting/stopping services requires explicit enable and confirmation")
    return [" ".join(["systemctl", a, shlex.quote(s)])]
