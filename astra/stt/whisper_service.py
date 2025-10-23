from __future__ import annotations

import io
import tempfile
from functools import lru_cache
import logging
from typing import Any, Dict, List, Tuple

from ..agent.config import config


try:
    from faster_whisper import WhisperModel  # type: ignore
except Exception:  # pragma: no cover
    WhisperModel = None  # type: ignore


_backend_used: str | None = None
_compute_type_used: str | None = None


@lru_cache(maxsize=1)
def _load_model() -> Any:
    global _backend_used, _compute_type_used
    if WhisperModel is None:
        raise RuntimeError("faster-whisper is not installed. Please install it in your environment.")
    preferred_device = config.whisper_device if config.whisper_device in {"cpu", "cuda"} else "auto"
    try:
        model = WhisperModel(
            model_size_or_path=config.whisper_model,
            device=preferred_device,
            compute_type=config.whisper_compute_type,
        )
        _backend_used = preferred_device
        _compute_type_used = config.whisper_compute_type
        return model
    except Exception as e:
        # Transparent CPU fallback if CUDA/cuDNN is not available
        logging.warning("Whisper init failed on device '%s' (%s). Falling back to CPU.", preferred_device, e)
        model = WhisperModel(
            model_size_or_path=config.whisper_model,
            device="cpu",
            compute_type="int8",
        )
        _backend_used = "cpu"
        _compute_type_used = "int8"
        return model


def stt_health() -> Dict[str, Any]:
    try:
        _ = _load_model()
        return {
            "ready": True,
            "model": config.whisper_model,
            "device_config": config.whisper_device,
            "device_used": _backend_used,
            "compute_type_used": _compute_type_used,
        }
    except Exception as e:
        return {"ready": False, "error": str(e)}


def transcribe_bytes(data: bytes, language: str | None = None) -> Dict[str, Any]:
    """Transcribe an audio file given as bytes using faster-whisper.

    Requirements: system ffmpeg for decoding many formats.
    """
    model = _load_model()
    # Write to a temp file to let ffmpeg handle formats
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        segments, info = model.transcribe(
            tmp.name,
            vad_filter=config.whisper_vad,
            language=language or config.whisper_language,
            beam_size=config.whisper_beam_size,
            initial_prompt=config.whisper_initial_prompt,
        )
        segs: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        for seg in segments:
            segs.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
            })
            text_parts.append(seg.text)
        return {
            "language": info.language,
            "duration": getattr(info, "duration", None),
            "text": " ".join(text_parts).strip(),
            "segments": segs,
        }

