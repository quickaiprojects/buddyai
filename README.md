# Buddy - Setup (Windows)

## 1. Install Python packages

Open a terminal in this folder and run:

```
pip install -r requirements.txt
```

## 2. Install Ollama and pull the model

Download and install Ollama from https://ollama.com/download (Windows installer).

Then in a terminal:

```
ollama pull qwen3:4b
```

Leave Ollama running in the background (it starts automatically after install and runs as a background service).

## 3. Install Piper (for spoken replies)

Piper is the local text-to-speech engine. It's a standalone executable, not a pip package.

1. Go to https://github.com/rhasspy/piper/releases
2. Download the latest Windows release (a `.zip`, something like `piper_windows_amd64.zip`)
3. Extract it, and copy `piper.exe` (and its accompanying `.dll` files) into this project's `piper/` folder, so you end up with:
   ```
   buddy/piper/piper.exe
   ```

## 4. Get a voice

1. Go to https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US
2. Pick a voice folder, e.g. `en_US/lessac/medium`
3. Download both files inside it:
   - `en_US-lessac-medium.onnx`
   - `en_US-lessac-medium.onnx.json`
4. Put both in this project's `voices/` folder:
   ```
   buddy/voices/en_US-lessac-medium.onnx
   buddy/voices/en_US-lessac-medium.onnx.json
   ```

This matches the default in `config.py` (`tts_voice: "en_US-lessac-medium"`), so it'll work out of the box.

### Trying other voices

Piper has dozens of English voices (different accents, male/female, expressiveness) at that same Hugging Face link, under `en/en_US/*` and `en/en_GB/*`. To switch:

1. Download the new `.onnx` + `.onnx.json` pair into `voices/`
2. Open Buddy, click the **⚙ settings** button, and change "TTS voice" to the new filename (no extension) - e.g. `en_US-amy-medium`
3. Click OK - the next reply will use the new voice

A few good starting points if you want to compare:
- `en_US-lessac-medium` - neutral, clear (the default)
- `en_US-amy-medium` - warmer female voice
- `en_US-ryan-medium` - male voice, more casual tone
- `en_GB-alan-medium` - British male

Each voice is roughly 30-60MB, so it's cheap to download a few and pick your favorite.

## 5. Volume and speed

In settings you can also adjust:
- **TTS volume** - defaults to 60%, so Buddy doesn't blast out at full system volume. Slide it up or down anytime.
- **TTS speed** - defaults to normal (1.0x). Lower = slower/calmer, higher = faster.
- **Speak responses automatically** - uncheck this if you want Buddy to only reply in text sometimes; you can still trigger speech by re-enabling it.

## 6. Run it

```
python main.py
```

Type a message and hit Enter or click Send. Buddy will reply in the chat and, if auto-speak is on, say it out loud. Click **Stop** anytime to cut off speech immediately.

Try:
```
open calculator
```
and Calculator should actually open - that's the tool-calling system working, not just talk.

## What's not in this version

Voice input (microphone / push-to-talk) isn't wired up yet - this build is text-in, voice-out. The architecture (separate `tools.py`, `llm.py`, `tts.py`, `ui.py`) is set up so voice input can be added later as its own module without touching the rest.






# NOT EVERY FILE IS IN THIS GITHUB PAGE GO TO THIS WEBSITE TO DOWNLOAD THE REST:
https://mega.nz/folder/SpgEFDBS#ATs4BSWGioCR95FF0kAYxA < PIPER
https://mega.nz/folder/jx5C2JCI#rMmVARbKL8gIi8mmo83Pvw < VOICES

add these folders to the buddyai\buddy\ for everything to work, thanks!!
