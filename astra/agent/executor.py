from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from .config import config
from .utils import requires_confirmation


WHITELIST = {
    "apps": {"firefox", "code", "gnome-terminal", "nautilus"},
    "service_actions": {"start", "stop", "restart", "status"},
    "services": {"sshd", "bluetooth", "cups", "NetworkManager"},
    "commands": {
        # safe-ish commands; arguments limited by sanitizers in skills
        "ls",
        "cp",
        "mv",
        "cat",
        "head",
        "tail",
        "echo",
        "pwd",
        "whoami",
        "uname",
        "df",
        "du",
        "free",
        "date",
        "flatpak",
    },
}

# Minimal safe environment passthrough for GUI apps and session-bound tools
ALLOWED_ENV_PASSTHROUGH = {
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "XAUTHORITY",
    "XDG_SESSION_TYPE",
    "XDG_CURRENT_DESKTOP",
    "DESKTOP_SESSION",
    "GDMSESSION",
    "KDE_FULL_SESSION",
    "QT_QPA_PLATFORM",
    # Non-sensitive basics that many tools expect
    "HOME",
    "SHELL",
}


@dataclass
class ExecResult:
    command: str
    stdout: str
    stderr: str
    returncode: int


def _run_subprocess(cmd: List[str], env: Optional[dict] = None) -> ExecResult:
    # Never escalate; set constrained environment
    env_vars = {
        "PATH": os.environ.get("PATH", ""),
        "LC_ALL": "C.UTF-8",
        "LANG": "C.UTF-8",
    }
    # Pass through selected session variables required for GUI/DBus interactions
    for key in ALLOWED_ENV_PASSTHROUGH:
        if key in os.environ:
            env_vars[key] = os.environ[key]
    if env:
        env_vars.update(env)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env_vars,
        check=False,
    )
    return ExecResult(
        command=" ".join(shlex.quote(c) for c in cmd),
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
        returncode=proc.returncode,
    )


def execute_safe(commands: List[str], confirm: bool = False, dry_run: bool = True) -> List[ExecResult]:
    results: List[ExecResult] = []
    for raw in commands:
        if "sudo" in raw:
            results.append(
                ExecResult(raw, "", "sudo not allowed without explicit feature enable", 1)
            )
            continue

        if requires_confirmation(raw) and not confirm:
            results.append(ExecResult(raw, "", "confirmation required", 2))
            continue

        if dry_run:
            results.append(ExecResult(raw, "dry-run: not executed", "", 0))
            continue

        # split safely
        parts = shlex.split(raw)
        # If this looks like a GUI launch but no display is available, fail fast with a helpful message
        if (
            (parts and parts[0] in {"gtk-launch", "gio", "xdg-open", *WHITELIST["apps"]})
            and ("DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ)
        ):
            results.append(
                ExecResult(
                    raw,
                    "",
                    "No GUI session detected (DISPLAY/WAYLAND_DISPLAY not set). Start the server from your desktop session or export these vars.",
                    1,
                )
            )
            continue
        # Optional firejail: only for risky binaries, disabled by default
        if config.enable_firejail:
            parts = ["firejail", "--quiet", "--private"] + parts

        res = _run_subprocess(parts)
        results.append(res)
    return results
