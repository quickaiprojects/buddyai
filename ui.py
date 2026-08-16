"""
Buddy's desktop GUI. Owns no LLM/TTS logic directly - it calls into llm.py
and tts.py from background QThreads so the window never freezes while
Buddy is thinking or speaking.
"""

import sys

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QDialog,
    QSlider, QCheckBox, QFormLayout, QDialogButtonBox,
)

from config import Config
from conversation import Conversation
from state import BuddyState
import llm
import tts


# ---------------------------------------------------------------- workers --

class LLMWorker(QObject):
    thinking = Signal(str)   # incremental chunk of reasoning text
    finished = Signal(str)   # full final reply text
    failed = Signal(str)

    def __init__(self, conversation, model_name):
        super().__init__()
        self.conversation = conversation
        self.model_name = model_name

    def run(self):
        try:
            for kind, text in llm.stream_reply(self.conversation, self.model_name):
                if kind == "thinking":
                    self.thinking.emit(text)
                elif kind == "done":
                    self.finished.emit(text)
        except Exception as e:
            self.failed.emit(str(e))


class TTSWorker(QObject):
    finished = Signal()

    def __init__(self, text, voice, volume, rate):
        super().__init__()
        self.text = text
        self.voice = voice
        self.volume = volume
        self.rate = rate

    def run(self):
        try:
            tts.speak(self.text, self.voice, self.volume, self.rate)
        finally:
            self.finished.emit()


# ------------------------------------------------------------- chat bubble --

class MessageBubble(QFrame):
    def __init__(self, text, is_user):
        super().__init__()
        self.setObjectName("userBubble" if is_user else "buddyBubble")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)


# ------------------------------------------------------------ settings ui --

class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Buddy Settings")
        form = QFormLayout(self)

        self.model_edit = QLineEdit(config.get("llm_model"))
        form.addRow("LLM model:", self.model_edit)

        self.voice_edit = QLineEdit(config.get("tts_voice"))
        form.addRow("TTS voice:", self.voice_edit)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(config.get("tts_volume") * 100))
        form.addRow("TTS volume:", self.volume_slider)

        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(50, 200)
        self.rate_slider.setValue(int(config.get("tts_rate") * 100))
        form.addRow("TTS speed:", self.rate_slider)

        self.auto_speak_check = QCheckBox("Speak responses automatically")
        self.auto_speak_check.setChecked(config.get("auto_speak"))
        form.addRow(self.auto_speak_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def save(self):
        self.config.set("llm_model", self.model_edit.text().strip())
        self.config.set("tts_voice", self.voice_edit.text().strip())
        self.config.set("tts_volume", self.volume_slider.value() / 100)
        self.config.set("tts_rate", self.rate_slider.value() / 100)
        self.config.set("auto_speak", self.auto_speak_check.isChecked())


# ------------------------------------------------------------- main window --

class BuddyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.conversation = Conversation(
            system_prompt=self.config.get("system_prompt"),
            max_turns=self.config.get("context_turns"),
        )
        self.state = BuddyState.READY
        self._threads = []  # keep refs alive so QThreads aren't garbage collected
        self._thinking_buffer = ""

        self.setWindowTitle("Buddy")
        self.resize(420, 620)
        self._build_ui()
        self._apply_style()

    # -- ui construction ------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        header = QHBoxLayout()
        title = QLabel("Buddy")
        title.setObjectName("title")
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedWidth(36)
        self.settings_btn.clicked.connect(self.open_settings)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_conversation)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_dot)
        header.addWidget(self.status_label)
        header.addWidget(self.clear_btn)
        header.addWidget(self.settings_btn)
        outer.addLayout(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.addStretch()
        self.scroll_area.setWidget(self.chat_container)
        outer.addWidget(self.scroll_area, stretch=1)

        self.thinking_label = QLabel("")
        self.thinking_label.setObjectName("thinkingLabel")
        self.thinking_label.setWordWrap(True)
        self.thinking_label.hide()
        outer.addWidget(self.thinking_label)

        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message...")
        self.input_field.returnPressed.connect(self.send_message)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_speaking)

        input_row.addWidget(self.input_field)
        input_row.addWidget(self.send_btn)
        input_row.addWidget(self.stop_btn)
        outer.addLayout(input_row)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1f26; }
            QLabel#title { color: #f5f5f7; font-size: 18px; font-weight: 600; }
            QLabel#statusDot { color: #4caf50; font-size: 14px; }
            QLabel#statusLabel { color: #9a9ab0; font-size: 12px; margin-right: 8px; }
            QScrollArea { border: none; background-color: #1e1f26; }
            QWidget { background-color: #1e1f26; }
            QLineEdit {
                background-color: #2a2b35; color: #f5f5f7; border-radius: 8px;
                padding: 8px; border: 1px solid #3a3b48;
            }
            QPushButton {
                background-color: #3a3b48; color: #f5f5f7; border-radius: 8px;
                padding: 8px 14px; border: none;
            }
            QPushButton:hover { background-color: #4a4b5c; }
            QFrame#userBubble {
                background-color: #4b6bfb; border-radius: 10px; margin-left: 60px;
            }
            QFrame#buddyBubble {
                background-color: #2f303c; border-radius: 10px; margin-right: 60px;
            }
            QFrame#userBubble QLabel, QFrame#buddyBubble QLabel {
                color: #f5f5f7; font-size: 13px; background: transparent;
            }
            QLabel#thinkingLabel {
                color: rgba(245, 245, 247, 90);
                font-style: italic;
                font-size: 12px;
                padding: 2px 8px 6px 8px;
                background: transparent;
            }
        """)

    # -- state ------------------------------------------------------------

    def set_state(self, state: BuddyState):
        self.state = state
        colors = {
            BuddyState.READY: "#4caf50",
            BuddyState.THINKING: "#f5a623",
            BuddyState.SPEAKING: "#4b6bfb",
        }
        self.status_dot.setStyleSheet(f"color: {colors.get(state, '#4caf50')}; font-size: 14px;")
        self.status_label.setText(state.value)

    # -- chat ---------------------------------------------------------------

    def add_message(self, text, is_user):
        bubble = MessageBubble(text, is_user)
        row = QHBoxLayout()
        if is_user:
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()
        wrapper = QWidget()
        wrapper.setLayout(row)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, wrapper)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def send_message(self):
        text = self.input_field.text().strip()
        if not text or self.state == BuddyState.THINKING:
            return
        self.input_field.clear()
        self.add_message(text, is_user=True)
        self.conversation.add_user(text)
        self.set_state(BuddyState.THINKING)

        self._thinking_buffer = ""
        self.thinking_label.setText("")
        self.thinking_label.hide()

        thread = QThread()
        worker = LLMWorker(self.conversation, self.config.get("llm_model"))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.thinking.connect(self._on_thinking)
        worker.finished.connect(self._on_reply)
        worker.failed.connect(self._on_llm_error)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(lambda: self._threads.remove((thread, worker)))
        self._threads.append((thread, worker))
        thread.start()

    def _on_thinking(self, text_delta):
        self._thinking_buffer += text_delta
        self.thinking_label.setText(self._thinking_buffer)
        self.thinking_label.show()
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def _clear_thinking(self):
        self._thinking_buffer = ""
        self.thinking_label.setText("")
        self.thinking_label.hide()

    def _on_reply(self, reply_text):
        self._clear_thinking()
        self.add_message(reply_text, is_user=False)
        if self.config.get("auto_speak"):
            self.speak_text(reply_text)
        else:
            self.set_state(BuddyState.READY)

    def _on_llm_error(self, error_text):
        self._clear_thinking()
        self.add_message(f"(couldn't reach the local model: {error_text})", is_user=False)
        self.set_state(BuddyState.READY)

    # -- tts ---------------------------------------------------------------

    def speak_text(self, text):
        self.set_state(BuddyState.SPEAKING)
        thread = QThread()
        worker = TTSWorker(
            text,
            self.config.get("tts_voice"),
            self.config.get("tts_volume"),
            self.config.get("tts_rate"),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda: self.set_state(BuddyState.READY))
        worker.finished.connect(thread.quit)
        thread.finished.connect(lambda: self._threads.remove((thread, worker)))
        self._threads.append((thread, worker))
        thread.start()

    def stop_speaking(self):
        tts.stop_speaking()

    # -- misc ---------------------------------------------------------------

    def clear_conversation(self):
        self.conversation.clear()
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.Accepted:
            dialog.save()


def main():
    app = QApplication(sys.argv)
    window = BuddyWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
