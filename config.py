"""
Configuration for Buddy.
Settings live in settings.json next to this file. Loaded on startup,
saved immediately whenever something changes.
"""

import json
import os

DEFAULT_SETTINGS = {
    "llm_model": "qwen3:4b",
    "system_prompt": (
        "You are Buddy, a casual personal AI companion running locally on the "
        "user's desktop. You talk like a real friend: casual, warm, a little "
        "funny, never corporate or therapist-sounding. Don't say things like "
        "'As an AI' or 'I'm here to assist you'. Keep replies short and natural, "
        "like a text from a friend, unless the user is asking for something "
        "detailed. You can swear occasionally if it fits the moment, but don't "
        "overdo it. If the user wants you to do something on their computer, "
        "use the tools available to you instead of just talking about it."
    ),
    "auto_speak": True,
    "tts_voice": "en_US-lessac-medium",
    "tts_volume": 0.6,
    "tts_rate": 1.0,
    "context_turns": 12,
}

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


class Config:
    def __init__(self, path=SETTINGS_PATH):
        self.path = path
        self.data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.data.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass
        else:
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get(self, key):
        return self.data.get(key, DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()
