from __future__ import annotations

import threading

try:
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None


class TTS:
    def __init__(self) -> None:
        self.engine = None
        if pyttsx3:
            try:
                self.engine = pyttsx3.init()
            except Exception:
                self.engine = None

    def say(self, text: str) -> None:
        if not self.engine:
            print(f"TTS: {text}")
            return

        def _speak():
            self.engine.say(text)
            self.engine.runAndWait()

        threading.Thread(target=_speak, daemon=True).start()


tts = TTS()
