# core/tools.py
# Central tool registry for Jarvis (hybrid routing)

from skills.system import open_app, tell_time
from skills.web import web_search
from skills.notes import save_note, list_notes
from skills.timer import set_timer

TOOL_REGISTRY = {
    "open_app": open_app,
    "tell_time": tell_time,
    "web_search": web_search,
    "save_note": save_note,
    "list_notes": list_notes,
    "set_timer": set_timer,
}
