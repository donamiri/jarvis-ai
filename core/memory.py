# store + retrieve

import json, time
from pathlib import Path

class Memory:
    def __init__(self, path="memory.json"):
        self.path = Path(path)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def save(self, user_text, assistant_text):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data.append({
            "ts": int(time.time()),
            "user": user_text,
            "assistant": assistant_text
        })
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
