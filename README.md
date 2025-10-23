# Astra — Hybrid local+cloud agentic voice assistant (Linux, Fedora-first)

MVP features:
- FastAPI agent controller (local HTTP)
- Intent parsing for open_app, run_command, manage_service
- Safe executor with whitelist, dry-run, and confirmations
- Model router with local-first policy and cloud stub
- TTS (pyttsx3) offline; STT stub for later
- Encrypted audit logs (Fernet)

## Quick start (local-only)

1) Create venv and install (optional if you already have one):

```bash
python3 -m venv ai
source ai/bin/activate
pip install -e ".[dev]"
```

2) Run API:

```bash
uvicorn astra.agent.main:app --host 127.0.0.1 --port 3110 --reload
```

3) Test intent -> plan -> execute (dry-run default):

```bash
curl -X POST http://127.0.0.1:3110/v1/ingress/transcript -H "Content-Type: application/json" \
  -d '{"transcript": "open firefox and show me fedora docs"}'
```

4) Execute with explicit confirmation (non-dry-run):

```bash
curl -X POST http://127.0.0.1:3110/v1/execute -H "Content-Type: application/json" \
  -d '{"commands": ["gtk-launch firefox"], "confirm": true, "dry_run": false}'
```

Notes:
- Whitelist is strict. Sudo and destructive commands are blocked by default.
- Local model and cloud adapters are stubs; integrate Ollama/OpenAI later.
- To change defaults, create a `.env` (see `.env.example`).

## Env variables (.env)

```env
ASTRA_HOST=127.0.0.1
ASTRA_PORT=3110
ASTRA_COMPLEXITY_TOKENS=800
ASTRA_FORCE_CLOUD=false
ASTRA_ALLOW_CLOUD=false
ASTRA_ENABLE_FIREJAIL=false
ASTRA_AUDIT_DIR=astra/data/audit
ASTRA_AUDIT_KEY=astra/data/audit/key.fernet
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=mistral
OLLAMA_TEMPERATURE=0.2
OLLAMA_TOP_P=0.95
OLLAMA_REPEAT_PENALTY=1.1
ASTRA_HTTP_TIMEOUT=10
OPENAI_API_KEY=
```

## New: LLM test endpoint

- Local-first by default. If you run Ollama with `mistral` available, the local adapter will respond.
- If cloud is enabled and selected by the router, PII is scrubbed before upload.

Example:

```bash
curl -s -X POST http://127.0.0.1:3110/v1/llm/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Summarize: Fedora uses DNF for package management.",
    "user_prefs": {"force_cloud": false}
  }' | jq .
```

### Optional: run Ollama locally

```bash
# Install and run Ollama (see ollama.com for platform instructions)
# Then pull a model and start the server
ollama pull mistral
ollama serve
```

Set `OLLAMA_URL` and `OLLAMA_MODEL` in `.env` if not default.

## Offline STT (faster-whisper)

Requirements:
- System ffmpeg installed (for decoding many audio formats).

Config in `.env`:

```env
WHISPER_MODEL=base           # tiny|base|small|medium|large-v3, etc.
WHISPER_DEVICE=auto          # auto|cpu|cuda
WHISPER_COMPUTE_TYPE=int8    # int8|int8_float32|float16|float32
WHISPER_VAD=true             # apply VAD filter
WHISPER_LANGUAGE=            # optional hint like en, hi, en-IN
WHISPER_BEAM_SIZE=5          # increase for accuracy (slower)
WHISPER_INITIAL_PROMPT=      # optional domain prompt, e.g., Linux app names
```

Health check:

```bash
curl -s http://127.0.0.1:3110/v1/stt/health | jq .
```

Transcribe an audio file (wav/mp3/ogg):

```bash
curl -s -X POST http://127.0.0.1:3110/v1/stt/transcribe \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/audio.wav" | jq .
```

Specify language per request (helps with accents and non-English):

```bash
curl -s -X POST http://127.0.0.1:3110/v1/stt/transcribe \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/audio.wav" \
  -F "language=en" | jq .
```

### Troubleshooting (GPU / cuDNN)

If you see errors like:

> Unable to load libcudnn_ops.so ... Cannot load symbol cudnnCreateTensorDescriptor

Either:
- Force CPU mode in `.env`:
  - `WHISPER_DEVICE=cpu`
  - `WHISPER_COMPUTE_TYPE=int8`
  - restart the server

or install the correct NVIDIA CUDA + cuDNN runtime matching your environment, and set:
- `WHISPER_DEVICE=cuda`
- `WHISPER_COMPUTE_TYPE=float16`

Note: Astra now auto-falls back to CPU if CUDA init fails.

## Push-to-talk (mic)

Run the simple CLI that records until you press Enter, transcribes, plans, and optionally executes:

```bash
"/home/kenx1kaneki/Desktop/AI assistant/ai/bin/python" -m astra.stt.ptt_cli
```

Requirements:
- Working microphone and default input device configured (PulseAudio/PipeWire).
- Python packages installed in your venv (already added): sounddevice, numpy.

Flow:
1) Press Enter to start recording.
2) Press Enter again to stop.
3) It transcribes the audio and shows a dry-run plan.
4) Type "y" to execute with confirmation safeguards.

Tip: set `ASTRA_STT_LANGUAGE=en` in your environment to send a per-request language hint from the CLI (e.g., `en`, `hi`, `en-IN`).

#### Override system prompt and options per request

```bash
curl -s -X POST http://127.0.0.1:3110/v1/llm/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "List three Fedora package managers.",
    "system_prompt": "You are Astra; answer in one short line.",
    "options": {"temperature": 0.1}
  }' | jq .
```

## systemd (user) auto-start

A user service is provided at `infra/systemd/astra.service`.

Steps:

```bash
# Copy as a user service
mkdir -p ~/.config/systemd/user
cp infra/systemd/astra.service ~/.config/systemd/user/

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable astra.service
systemctl --user start astra.service

# Check logs
journalctl --user -u astra.service -f
```

If your venv or project path differ, edit `ExecStart` and `WorkingDirectory` in the service file accordingly.