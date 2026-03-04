# voice/tts.py
import subprocess
import re

MASTER_NAME = "Master Mike"

# When to add the name:
# - Always when forced (startup/errors)
# - Otherwise only for longer/important messages
MIN_WORDS_FOR_NAME = 6  # tweak if you want (e.g., 8)


def _should_address(text: str, force: bool) -> bool:
    if force:
        return True

    t = (text or "").strip().lower()
    if not t:
        return False

    # If it's already addressing you, don't double it
    if MASTER_NAME.lower() in t:
        return False

    # Always address on warnings/errors/critical system messages
    keywords = [
        "error", "failed", "can't", "cannot", "unable", "exception",
        "warning", "problem", "issue", "shutting down", "restart", "restarting",
        "online", "offline", "ready", "boot", "initialized",
    ]
    if any(k in t for k in keywords):
        return True

    # Address if it's a longer response
    words = re.findall(r"\w+", t)
    return len(words) >= MIN_WORDS_FOR_NAME


def speak(text: str, *, force_name: bool = False):
    text = "" if text is None else str(text).strip()
    if not text:
        return

    line = f"{MASTER_NAME}, {text}" if _should_address(text, force_name) else text

    print(f"JARVIS: {line}")

    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.Rate = 0; $s.Volume = 100; "
        "$s.Speak([Console]::In.ReadToEnd())"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=line, text=True)