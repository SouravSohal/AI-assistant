from __future__ import annotations

from dataclasses import dataclass

from .config import config
from .utils import estimate_token_count, is_privacy_sensitive, intent_is_system_action
from ..models.local_mistral_adapter import LocalAdapter
from ..models.cloud_adapter import CloudAdapter


@dataclass
class RoutedModel:
    name: str
    adapter: object
    reason: str


def route_request(transcript: str, context: dict, user_prefs: dict | None = None) -> RoutedModel:
    user_prefs = user_prefs or {}
    if user_prefs.get("force_cloud") or config.force_cloud:
        return RoutedModel("cloud", CloudAdapter(config), reason="user override: force cloud")

    if is_privacy_sensitive(transcript) or intent_is_system_action(transcript):
        return RoutedModel("local", LocalAdapter(config), reason="privacy/system-action -> local")

    complexity = estimate_token_count(transcript)
    if complexity > config.complexity_threshold_tokens and config.allow_cloud_uploads:
        return RoutedModel("cloud", CloudAdapter(config), reason=f"complexity {complexity} > threshold")

    return RoutedModel("local", LocalAdapter(config), reason="default local policy")
