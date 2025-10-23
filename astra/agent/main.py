from __future__ import annotations

from typing import Any, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from .config import config
from .audit import audit
from .model_router import route_request
from .privacy import scrub_text
from .intent_parser import parse_intent, llm_parse_intent
from .executor import execute_safe, ExecResult
from ..skills.open_app import build_open_app_plan
from ..skills.run_command import build_run_command_plan
from ..skills.manage_service import build_manage_service_plan
from ..tts.tts_engine import tts
from ..stt.whisper_service import stt_health, transcribe_bytes


app = FastAPI(title=config.app_name)


class TranscriptIn(BaseModel):
    transcript: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    user_prefs: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True
    confirm: bool = False


class ExecuteIn(BaseModel):
    commands: List[str]
    dry_run: bool = True
    confirm: bool = False


class ExecResultOut(BaseModel):
    command: str
    stdout: str
    stderr: str
    returncode: int


def plan_from_intent(text: str) -> List[str]:
    intent = parse_intent(text)
    if not intent:
        # Fallback to LLM-based intent extraction
        intent = llm_parse_intent(text)
    if not intent:
        raise HTTPException(status_code=400, detail="Could not parse intent")
    if intent.name == "open_app":
        return build_open_app_plan(intent.entities.get("app", ""))
    if intent.name == "manage_service":
        return build_manage_service_plan(
            intent.entities.get("action", ""), intent.entities.get("service", "")
        )
    if intent.name == "run_command":
        return build_run_command_plan(intent.entities.get("cmd", ""))
    raise HTTPException(status_code=400, detail=f"Unsupported intent: {intent.name}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/ingress/transcript", response_model=list[ExecResultOut])
def handle_transcript(payload: TranscriptIn):
    routed = route_request(payload.transcript, payload.context, payload.user_prefs)

    # For MVP, skip LLM planning and rely on deterministic intent parsing
    try:
        plan = plan_from_intent(payload.transcript)
    except HTTPException as e:
        audit.write({"event": "intent_failed", "text": payload.transcript, "error": str(e.detail)})
        raise

    audit.write(
        {
            "event": "route",
            "model": routed.name,
            "reason": routed.reason,
            "text": payload.transcript,
            "plan": plan,
            "dry_run": payload.dry_run,
        }
    )

    results: List[ExecResult] = execute_safe(plan, confirm=payload.confirm, dry_run=payload.dry_run)
    tts.say("Done. Check your terminal output.")
    return [
        ExecResultOut(command=r.command, stdout=r.stdout, stderr=r.stderr, returncode=r.returncode)
        for r in results
    ]


@app.post("/v1/execute", response_model=list[ExecResultOut])
def handle_execute(payload: ExecuteIn):
    audit.write({"event": "execute_request", "commands": payload.commands, "dry_run": payload.dry_run})
    results: List[ExecResult] = execute_safe(payload.commands, confirm=payload.confirm, dry_run=payload.dry_run)
    return [
        ExecResultOut(command=r.command, stdout=r.stdout, stderr=r.stderr, returncode=r.returncode)
        for r in results
    ]


class LLMIn(BaseModel):
    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)
    user_prefs: dict[str, Any] = Field(default_factory=dict)
    scrub_privacy: bool = True
    system_prompt: str | None = None
    options: dict[str, Any] | None = None


class LLMOut(BaseModel):
    model: str
    reason: str
    text: str
    confidence: float
    error: str | None = None


@app.post("/v1/llm/complete", response_model=LLMOut)
def llm_complete(payload: LLMIn):
    routed = route_request(payload.prompt, payload.context, payload.user_prefs)
    prompt = payload.prompt
    # Scrub only for cloud uploads
    if routed.name == "cloud" and payload.scrub_privacy:
        prompt = scrub_text(prompt)

    try:
        # Pass through optional overrides if the adapter supports them
        ctx = dict(payload.context)
        if payload.system_prompt:
            ctx["system_prompt_override"] = payload.system_prompt
        if payload.options:
            ctx["gen_options_override"] = payload.options
        out = routed.adapter.predict(prompt, ctx)
    except Exception as e:
        audit.write({"event": "llm_error", "model": routed.name, "error": str(e)})
        raise HTTPException(status_code=500, detail="LLM call failed")

    text = out.get("text", "")
    confidence = float(out.get("confidence", 0.0))
    error = out.get("error")
    audit.write({
        "event": "llm_complete",
        "model": routed.name,
        "reason": routed.reason,
        "confidence": confidence,
        "error": error,
    })
    return LLMOut(model=routed.name, reason=routed.reason, text=text, confidence=confidence, error=error)


@app.get("/v1/stt/health")
def stt_health_check():
    return stt_health()


class STTOut(BaseModel):
    text: str
    language: str | None = None
    duration: float | None = None
    segments: list[dict] | None = None


@app.post("/v1/stt/transcribe", response_model=STTOut)
async def stt_transcribe(file: UploadFile = File(...), language: str | None = Form(None)):
    data = await file.read()
    result = transcribe_bytes(data, language=language)
    return STTOut(
        text=result.get("text", ""),
        language=result.get("language"),
        duration=result.get("duration"),
        segments=result.get("segments"),
    )
