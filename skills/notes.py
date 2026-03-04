# save + recall
# skills/notes.py
import json
import time
from pathlib import Path

NOTES_FILE = Path("notes.json")

def _load():
    if not NOTES_FILE.exists():
        NOTES_FILE.write_text("[]", encoding="utf-8")
    return json.loads(NOTES_FILE.read_text(encoding="utf-8"))

def _save(data):
    NOTES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def save_note(content: str) -> str:
    data = _load()
    data.append({"ts": int(time.time()), "content": content})
    _save(data)
    return "Saved."

def list_notes(limit: int = 10) -> str:
    data = _load()
    latest = list(reversed(data))[:limit]
    if not latest:
        return "No notes yet."
    lines = []
    for item in latest:
        lines.append(f"- {item['content']}")
    return "Here are your latest notes:\n" + "\n".join(lines)
