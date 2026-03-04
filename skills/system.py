# skills/system.py
import os
import subprocess
import webbrowser
from datetime import datetime
from difflib import get_close_matches

from skills.app_indexer import load_index, build_index


def tell_time() -> str:
    return datetime.now().strftime("It is %I:%M %p.")


# Hardcoded fast aliases (optional, but handy)
ALIASES = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vs code": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "spotify": "spotify.exe",
    "whatsapp": "whatsapp://",
}

# Websites you want to open even if no desktop app exists
WEB_ALIASES = {
    "github": "https://github.com",
    "github.com": "https://github.com",
    "youtube": "https://youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://google.com",
    "chatgpt": "https://chat.openai.com",
    "spotify web": "https://open.spotify.com",
}


def _open_target(target: str):
    target = os.path.expandvars(target)

    # URI scheme (whatsapp:// etc.)
    if "://" in target and not target.lower().endswith(".exe"):
        os.startfile(target)
        return

    # Start menu shortcut
    if target.lower().endswith(".lnk"):
        os.startfile(target)
        return

    # Normal executable/command
    subprocess.Popen(target)


def open_app(name: str) -> str:
    name = (name or "").lower().strip()
    if not name:
        return "Tell me what to open."

    # 1) Web aliases (GitHub etc.)
    if name in WEB_ALIASES:
        webbrowser.open(WEB_ALIASES[name])
        return f"Opening {name}."

    # 2) Hard aliases
    if name in ALIASES:
        try:
            _open_target(ALIASES[name])
            return f"Opening {name}."
        except Exception as e:
            return f"Couldn't open {name}: {e}"

    # 3) App index from Start Menu
    apps = load_index()
    if not apps:
        apps = build_index()

    # Exact match
    if name in apps:
        try:
            _open_target(apps[name])
            return f"Opening {name}."
        except Exception as e:
            return f"Couldn't open {name}: {e}"

    # Fuzzy match
    candidates = get_close_matches(name, apps.keys(), n=5, cutoff=0.55)
    if candidates:
        best = candidates[0]
        try:
            _open_target(apps[best])
            return f"Opening {best}."
        except Exception as e:
            return f"Couldn't open {best}: {e}"

    # If user said "open github desktop" but it isn't installed
    if "github" in name:
        webbrowser.open("https://github.com")
        return "I couldn't find a GitHub desktop app, so I opened GitHub in your browser."

    return f"I couldn't find '{name}'. Try 'reindex apps' or check the app name."