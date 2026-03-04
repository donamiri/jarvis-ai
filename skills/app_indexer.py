# skills/app_indexer.py
import json
import os
from pathlib import Path
import re

# Where we store the app index
APPS_DB = Path("apps.json")

START_MENU_DIRS = [
    Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
    Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
]

def _clean_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"\.lnk$", "", name)
    name = re.sub(r"[^a-z0-9\s\-_.()]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

def build_index() -> dict:
    apps = {}

    for base in START_MENU_DIRS:
        if not base.exists():
            continue

        for path in base.rglob("*.lnk"):
            display = _clean_name(path.stem)
            # Keep the shortest path for duplicates, usually the "main" shortcut
            if display not in apps or len(str(path)) < len(apps[display]):
                apps[display] = str(path)

    APPS_DB.write_text(json.dumps(apps, indent=2), encoding="utf-8")
    return apps

def load_index() -> dict:
    if not APPS_DB.exists():
        return {}
    return json.loads(APPS_DB.read_text(encoding="utf-8"))