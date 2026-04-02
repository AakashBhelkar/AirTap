"""Voice command listener — runs in a background thread, always listening.

Uses Google Web Speech API (online) as primary, Vosk (offline) as fallback.
"""

import json
import os
import shutil
import threading
import time
import zipfile
from enum import Enum
from pathlib import Path

import speech_recognition as sr

from config import VOSK_MODEL_NAME, VOSK_MODEL_URL, VOSK_MODEL_DIR


class MicStatus(Enum):
    LISTENING = "listening"    # green
    PROCESSING = "processing"  # red
    DISABLED = "disabled"      # grey
    ERROR = "error"            # grey


# Voice commands mapped to action keys
_COMMANDS = {
    "airtap on": "enable",
    "air tap on": "enable",
    "airtap off": "disable",
    "air tap off": "disable",
    "presentation mode": "mode_presentation",
    "media mode": "mode_media",
    "daily mode": "mode_daily",
    "calibrate": "calibrate",
    "take screenshot": "screenshot",
    "take a screenshot": "screenshot",
}


class VoiceListener:
    """Background voice command listener with online/offline recognition."""

    def __init__(self):
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = 300
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = 0.6

        self._mic: sr.Microphone | None = None
        self._status = MicStatus.DISABLED
        self._lock = threading.Lock()
        self._running = False
        self._callbacks: list = []  # fn(action_key: str)

        # Vosk fallback
        self._vosk_model = None
        self._use_vosk = False

        # Try to init microphone
        try:
            self._mic = sr.Microphone()
            # Quick test
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            self._status = MicStatus.LISTENING
            print("[Voice] Microphone ready")
        except (OSError, AttributeError, sr.RequestError) as e:
            print(f"[Voice] No microphone available: {e}")
            print("[Voice] Voice commands disabled — keyboard-only mode")
            self._mic = None
            self._status = MicStatus.DISABLED

    @property
    def status(self) -> MicStatus:
        with self._lock:
            return self._status

    def on_command(self, callback):
        """Register callback fn(action_key: str)."""
        self._callbacks.append(callback)

    def start(self):
        if self._mic is None:
            return
        self._running = True
        t = threading.Thread(target=self._listen_loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------
    # Main listen loop
    # ------------------------------------------------------------------

    def _listen_loop(self):
        while self._running:
            if self._mic is None:
                time.sleep(1)
                continue

            try:
                with self._lock:
                    self._status = MicStatus.LISTENING

                with self._mic as source:
                    audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=4)

                with self._lock:
                    self._status = MicStatus.PROCESSING

                text = self._recognize(audio)
                if text:
                    self._process_text(text)

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print(f"[Voice] Error: {e}")
                with self._lock:
                    self._status = MicStatus.ERROR
                time.sleep(1)

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------

    def _recognize(self, audio: sr.AudioData) -> str | None:
        """Try Google first, fall back to Vosk offline."""
        # Try Google Web Speech (online)
        try:
            text = self._recognizer.recognize_google(audio)
            return text.lower().strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            pass  # network issue — fall through to Vosk

        # Vosk offline fallback
        return self._recognize_vosk(audio)

    def _recognize_vosk(self, audio: sr.AudioData) -> str | None:
        """Offline recognition using Vosk."""
        try:
            from vosk import Model, KaldiRecognizer
        except ImportError:
            return None

        if self._vosk_model is None:
            model_path = self._ensure_vosk_model()
            if model_path is None:
                return None
            self._vosk_model = Model(model_path)

        rec = KaldiRecognizer(self._vosk_model, 16000)
        # Convert audio to raw PCM 16kHz mono
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        rec.AcceptWaveform(raw)
        result = json.loads(rec.FinalResult())
        text = result.get("text", "").strip()
        return text if text else None

    # ------------------------------------------------------------------
    # Vosk model management
    # ------------------------------------------------------------------

    def _ensure_vosk_model(self) -> str | None:
        """Download Vosk model if not present. Returns model directory path."""
        model_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), VOSK_MODEL_DIR
        )
        model_path = os.path.join(model_dir, VOSK_MODEL_NAME)

        if os.path.isdir(model_path):
            return model_path

        print(f"[Voice] Downloading Vosk model ({VOSK_MODEL_NAME})...")
        os.makedirs(model_dir, exist_ok=True)
        zip_path = os.path.join(model_dir, f"{VOSK_MODEL_NAME}.zip")

        try:
            import requests
            resp = requests.get(VOSK_MODEL_URL, stream=True, timeout=60)
            resp.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(model_dir)

            os.remove(zip_path)
            print(f"[Voice] Vosk model ready: {model_path}")
            return model_path
        except Exception as e:
            print(f"[Voice] Failed to download Vosk model: {e}")
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return None

    # ------------------------------------------------------------------
    # Command matching
    # ------------------------------------------------------------------

    def _process_text(self, text: str):
        """Match recognized text against known commands."""
        for phrase, action_key in _COMMANDS.items():
            if phrase in text:
                print(f"[Voice] Recognized: '{text}' → {action_key}")
                for cb in self._callbacks:
                    try:
                        cb(action_key)
                    except Exception as e:
                        print(f"[Voice] Callback error: {e}")
                return

        # No match — ignore
