"""
Short-term conversation memory: just the current session's messages, trimmed
so the prompt sent to the model doesn't grow forever.
"""


class Conversation:
    def __init__(self, system_prompt: str, max_turns: int = 12):
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.messages = []  # list of {"role": ..., "content": ...}

    def add_user(self, text: str):
        self.messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant(self, text: str):
        self.messages.append({"role": "assistant", "content": text})
        self._trim()

    def add_tool_result(self, tool_name: str, result: str):
        self.messages.append({"role": "tool", "content": result, "name": tool_name})
        self._trim()

    def _trim(self):
        limit = self.max_turns * 2
        if len(self.messages) > limit:
            self.messages = self.messages[-limit:]

    def as_ollama_messages(self):
        return [{"role": "system", "content": self.system_prompt}] + self.messages

    def clear(self):
        self.messages = []
