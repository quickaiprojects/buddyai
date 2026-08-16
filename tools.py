"""
Tool registry for Buddy. The LLM never touches the OS directly - it can only
request one of these functions by name, and Python decides whether/how to
actually run it. Add new tools by writing a function + schema and registering
it in TOOLS below.
"""

import os
import subprocess
import webbrowser
from datetime import datetime

# --- individual tool implementations ---------------------------------------

# Common Windows app name -> executable shortcuts. Anything not listed here
# is tried directly as "<name>.exe", which works for most installed apps
# that are already on PATH (chrome, spotify, etc.).
KNOWN_APPS = {
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
}


def open_application(name: str) -> str:
    key = name.strip().lower()
    exe = KNOWN_APPS.get(key, key if key.endswith(".exe") else key + ".exe")
    try:
        subprocess.Popen(exe, shell=True)
        return f"Opened {name}."
    except Exception as e:
        return f"Couldn't open {name}: {e}"


def close_application(name: str) -> str:
    key = name.strip().lower()
    exe = KNOWN_APPS.get(key, key if key.endswith(".exe") else key + ".exe")
    try:
        subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True)
        return f"Closed {name}."
    except Exception as e:
        return f"Couldn't close {name}: {e}"


def open_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}."


def get_current_time() -> str:
    return datetime.now().strftime("%I:%M %p on %A, %B %d")


def search_files(query: str) -> str:
    matches = []
    home = os.path.expanduser("~")
    for root, dirs, files in os.walk(home):
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d.lower() not in ("appdata", "node_modules")
        ]
        for f in files:
            if query.lower() in f.lower():
                matches.append(os.path.join(root, f))
        if len(matches) >= 15:
            break
    if not matches:
        return f"No files found matching '{query}'."
    return "Found:\n" + "\n".join(matches[:15])


# --- registry ----------------------------------------------------------------
# Each entry pairs the Python function with the JSON schema Ollama needs to
# know it exists and how to call it.

TOOLS = {
    "open_application": {
        "function": open_application,
        "schema": {
            "type": "function",
            "function": {
                "name": "open_application",
                "description": "Open a desktop application by name, e.g. 'calculator' or 'notepad'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the application to open"}
                    },
                    "required": ["name"],
                },
            },
        },
    },
    "close_application": {
        "function": close_application,
        "schema": {
            "type": "function",
            "function": {
                "name": "close_application",
                "description": "Close a running desktop application by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Name of the application to close"}
                    },
                    "required": ["name"],
                },
            },
        },
    },
    "open_url": {
        "function": open_url,
        "schema": {
            "type": "function",
            "function": {
                "name": "open_url",
                "description": "Open a URL in the default web browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to open"}
                    },
                    "required": ["url"],
                },
            },
        },
    },
    "get_current_time": {
        "function": get_current_time,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "Get the current date and time.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    },
    "search_files": {
        "function": search_files,
        "schema": {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search the user's home folder for files matching a name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Filename or partial filename to search for"}
                    },
                    "required": ["query"],
                },
            },
        },
    },
}


def get_schemas():
    return [t["schema"] for t in TOOLS.values()]


def execute(name: str, arguments: dict) -> str:
    if name not in TOOLS:
        return f"Unknown tool: {name}"
    try:
        return TOOLS[name]["function"](**arguments)
    except Exception as e:
        return f"Error running {name}: {e}"
