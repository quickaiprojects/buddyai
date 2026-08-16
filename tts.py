"""
Local text-to-speech using the Piper CLI (piper/piper.exe). Runs synthesis
and playback together so speech can be interrupted immediately by calling
stop_speaking() from any thread.

Voice files:
  Each Piper voice is two files - a .onnx model and a .onnx.json config -
  both go in the voices/ folder. tts_voice in settings.json is just the
  base filename (no extension), e.g. "en_US-lessac-medium".
"""

import json
import os
import subprocess
import threading

import numpy as np
import sounddevice as sd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PIPER_EXE = os.path.join(BASE_DIR, "piper", "piper.exe")
VOICES_DIR = os.path.join(BASE_DIR, "voices")

_stop_event = threading.Event()
_lock = threading.Lock()
_current_process = None


def _sample_rate_for(voice_name: str) -> int:
    config_path = os.path.join(VOICES_DIR, f"{voice_name}.onnx.json")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["audio"]["sample_rate"]


def speak(text: str, voice_name: str, volume: float = 0.6, rate: float = 1.0):
    """
    Synthesizes and plays `text` aloud. Call from a background thread only -
    this blocks until speech finishes or is interrupted.
    """
    global _current_process

    if not text.strip():
        return

    model_path = os.path.join(VOICES_DIR, f"{voice_name}.onnx")
    if not os.path.exists(model_path) or not os.path.exists(PIPER_EXE):
        # Fail quietly - the chat still works fine without TTS.
        print(f"[tts] Missing voice or piper.exe, skipping speech. Looked for: {model_path}")
        return

    with _lock:
        _stop_event.clear()
        sample_rate = _sample_rate_for(voice_name)
        length_scale = str(1.0 / max(rate, 0.1))

        _current_process = subprocess.Popen(
            [PIPER_EXE, "--model", model_path, "--output-raw", "--length-scale", length_scale],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        _current_process.stdin.write(text.encode("utf-8"))
        _current_process.stdin.close()

        stream = sd.OutputStream(samplerate=sample_rate, channels=1, dtype="int16")
        stream.start()
        chunk_size = 4096
        gain = max(0.0, min(volume, 1.0))

        try:
            while True:
                if _stop_event.is_set():
                    break
                data = _current_process.stdout.read(chunk_size)
                if not data:
                    break
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) * gain
                stream.write(samples.astype(np.int16))
        finally:
            stream.stop()
            stream.close()
            if _current_process.poll() is None:
                _current_process.terminate()
            _current_process = None


def stop_speaking():
    _stop_event.set()
    if _current_process is not None and _current_process.poll() is None:
        _current_process.terminate()
