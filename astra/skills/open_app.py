from __future__ import annotations

import shutil
from typing import List

from ..agent.executor import WHITELIST


def _sanitize_app(name: str) -> str:
    # Normalize case and strip common trailing punctuation that STT often adds
    name = name.strip().lower()
    name = name.strip(" .!?,;:'\"()[]{}")
    # collapse internal extra spaces
    name = " ".join(name.split())
    return name


def build_open_app_plan(app_name: str) -> List[str]:
    app = _sanitize_app(app_name)
    # normalize
    mapping = {
        "terminal": "gnome-terminal",
        "files": "nautilus",
    }
    app = mapping.get(app, app)
    if app not in WHITELIST["apps"]:
        raise ValueError(f"App '{app}' not allowed (whitelist).")

    # Prefer launching via the binary if available; it's more portable across desktops
    if shutil.which(app):
        return [app]

    # Fallback to gtk-launch with known desktop IDs
    desktop_ids = {
        "firefox": "org.mozilla.firefox",
        "gnome-terminal": "org.gnome.Terminal",
        "nautilus": "org.gnome.Nautilus",
        "code": "code",  # VS Code's desktop ID is usually 'code'
    }
    if shutil.which("gtk-launch") and app in desktop_ids:
        return [f"gtk-launch {desktop_ids[app]}"]

    # Flatpak fallback if binary not present (common on Fedora Silverblue/Workstation)
    flatpak_ids = {
        "firefox": "org.mozilla.firefox",
        "gnome-terminal": "org.gnome.Terminal",
        "nautilus": "org.gnome.Nautilus",
        "code": "com.visualstudio.code",  # sometimes 'com.visualstudio.code'
    }
    if shutil.which("flatpak") and app in flatpak_ids:
        return [f"flatpak run {flatpak_ids[app]}"]

    # Last resort: attempt direct name anyway
    return [app]
