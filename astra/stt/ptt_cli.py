from __future__ import annotations

import io
import os
import sys
import time
import queue
import threading
import wave
from typing import Optional

import numpy as np
import requests

try:
    import sounddevice as sd  # type: ignore
except Exception as e:
    print("Error: sounddevice is not available. Install it in your venv.", file=sys.stderr)
    raise


def record_until_enter(samplerate: int = 16000, channels: int = 1) -> bytes:
    q: queue.Queue[np.ndarray] = queue.Queue()
    stop_flag = threading.Event()

    def callback(indata, frames, t, status):
        if status:
            # Non-fatal warnings printed to stderr
            print(status, file=sys.stderr)
        q.put(indata.copy())

    # Open input stream
    with sd.InputStream(samplerate=samplerate, channels=channels, dtype="int16", callback=callback):
        print("Recording... Press Enter to stop.")

        def stopper():
            try:
                input()
            except EOFError:
                pass
            stop_flag.set()

        tthr = threading.Thread(target=stopper, daemon=True)
        tthr.start()

        frames = []
        while not stop_flag.is_set():
            try:
                chunk = q.get(timeout=0.1)
                frames.append(chunk)
            except queue.Empty:
                pass

    if not frames:
        return b""

    audio = np.concatenate(frames, axis=0)
    # Write to an in-memory WAV buffer
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16
        wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def main():
    host = os.getenv("ASTRA_HOST", "127.0.0.1")
    port = int(os.getenv("ASTRA_PORT", "3110"))
    base = f"http://{host}:{port}"
    stt_language = os.getenv("ASTRA_STT_LANGUAGE")

    print("Push-to-Talk: Press Enter to start recording.")
    try:
        input()
    except EOFError:
        pass

    try:
        data = record_until_enter()
        if not data:
            print("No audio captured.")
            return 0

        # Transcribe
        files = {"file": ("clip.wav", data, "audio/wav")}
        form = {}
        if stt_language:
            form["language"] = stt_language
        print("Transcribing...")
        resp = requests.post(f"{base}/v1/stt/transcribe", files=files, data=form or None, timeout=120)
        resp.raise_for_status()
        tr = resp.json()
        text = tr.get("text", "")
        print(f"Transcript: {text}")

        if not text.strip():
            return 0

        # Send to intent/plan/execute as a dry-run first
        payload = {"transcript": text, "dry_run": True}
        print("Planning (dry-run)...")
        resp2 = requests.post(f"{base}/v1/ingress/transcript", json=payload, timeout=60)
        if resp2.ok:
            print("Plan:")
            print(resp2.text)
        else:
            print("Planning failed:", resp2.status_code, resp2.text)

        # Optional: ask user to confirm execution
        ans = input("Execute this plan? [y/N]: ").strip().lower()
        if ans == "y":
            payload = {"transcript": text, "dry_run": False, "confirm": True}
            resp3 = requests.post(f"{base}/v1/ingress/transcript", json=payload, timeout=60)
            print("Execution result:")
            print(resp3.text)

    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
