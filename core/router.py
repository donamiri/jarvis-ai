# core/router.py
# Offline routing: rules first (no LLM required)

import re

from skills.system import open_app, tell_time
from skills.web import web_search
from skills.notes import save_note, list_notes
from skills.timer import set_timer
from skills.app_indexer import build_index
from skills.app_actions import (
    write_in_notepad,
    type_in_indexed_app,
    message_whatsapp,
    call_whatsapp,
    message_wechat,
    call_wechat,
    vpn_connect_proton,
    vpn_disconnect_proton,
    vpn_connect_hideme,
    vpn_disconnect_hideme,
)

from skills.spotify import (
    spotify_play,
    spotify_pause,
    spotify_resume,
    spotify_next,
    spotify_volume,
)


def _extract_timer_seconds(t: str) -> int | None:
    """
    Supports:
      - "set a timer for 10 seconds"
      - "timer 2 minutes"
      - "timer 1 minute 30 seconds"
      - "set timer 45"
    """
    # If user says just "timer 45" treat as seconds
    m = re.search(r"\b(timer|set timer)\b\s+(\d+)\b", t)
    if m:
        return int(m.group(2))

    mins = 0
    secs = 0

    mmin = re.search(r"(\d+)\s*(minute|minutes|min|mins)\b", t)
    if mmin:
        mins = int(mmin.group(1))

    msec = re.search(r"(\d+)\s*(second|seconds|sec|secs)\b", t)
    if msec:
        secs = int(msec.group(1))

    total = mins * 60 + secs
    return total if total > 0 else None


def route(text: str) -> dict:
    t = text.lower().strip()

    # ---------- OPEN ANY APP / WEBSITE ----------
    if t.startswith("open "):
        app_name = t.replace("open", "", 1).strip()
        return {"type": "tool", "tool": open_app, "args": {"name": app_name}}

    # ---------- REINDEX APPS ----------
    if any(p in t for p in ["reindex apps", "refresh apps", "scan apps"]):
        def _do_index():
            n = len(build_index())
            return f"Indexed {n} apps."
        return {"type": "tool", "tool": _do_index, "args": {}}

    # ---------- SPOTIFY ----------
    if t.startswith("play "):
        q = t.replace("play", "", 1).strip()
        return {"type": "tool", "tool": spotify_play, "args": {"query": q}}

    # "pause" / "pause spotify"
    if t in {"pause", "pause music"} or ("pause" in t and "spotify" in t):
        return {"type": "tool", "tool": spotify_pause, "args": {}}

    # "resume" / "continue"
    if t in {"resume", "continue"} or (("resume" in t or "continue" in t) and "spotify" in t):
        return {"type": "tool", "tool": spotify_resume, "args": {}}

    # "next" / "skip"
    if t in {"next", "skip"} or ("next" in t and "spotify" in t) or ("skip" in t and "spotify" in t):
        return {"type": "tool", "tool": spotify_next, "args": {}}

    # "volume 30" / "volume to 30"
    mvol = re.search(r"\bvolume\s*(to)?\s*(\d{1,3})\b", t)
    if mvol:
        return {"type": "tool", "tool": spotify_volume, "args": {"percent": int(mvol.group(2))}}

    # ---------- TIME ----------
    if "time" in t:
        return {"type": "tool", "tool": tell_time, "args": {}}

    # ---------- WEB SEARCH ----------
    if t.startswith("search ") or t.startswith("google "):
        query = (
            t.replace("google", "", 1)
            .replace("search", "", 1)
            .replace("for", "", 1)
            .strip()
        )
        if query:
            return {"type": "tool", "tool": web_search, "args": {"query": query}}

    # ---------- NOTES ----------
    if "remember that" in t:
        content = t.split("remember that", 1)[1].strip()
        if content:
            return {"type": "tool", "tool": save_note, "args": {"content": content}}

    if "show notes" in t or "list notes" in t:
        return {"type": "tool", "tool": list_notes, "args": {}}

    # ---------- TIMER ----------
    if "timer" in t:
        seconds = _extract_timer_seconds(t)
        if seconds:
            return {"type": "tool", "tool": set_timer, "args": {"seconds": seconds}}

    # ---------- WRITE / TYPE IN NOTEPAD ----------
    if "notepad" in t and ("write" in t or "type" in t):
        for pattern in [
            r"write\s+in\s+notepad[:\s]+(.+)",
            r"type\s+in\s+notepad[:\s]+(.+)",
            r"notepad\s+write[:\s]+(.+)",
            r"notepad\s+type[:\s]+(.+)",
        ]:
            m = re.search(pattern, t, re.IGNORECASE)
            if m:
                content = m.group(1).strip()
                if content:
                    return {"type": "tool", "tool": write_in_notepad, "args": {"text": content}}

    # ---------- WRITE / TYPE IN ANY INDEXED APP ----------
    m_type = re.search(r"(?:write|type)\s+in\s+([a-z0-9\s]+?)(?:\s*[:\-]\s*|\s+)(.+)", t)
    if m_type:
        app_part = m_type.group(1).strip()
        content = m_type.group(2).strip()
        if app_part and content:
            return {"type": "tool", "tool": type_in_indexed_app, "args": {"app_name": app_part, "text": content}}

    # ---------- WHATSAPP: MESSAGE / TEXT ----------
    if "whatsapp" in t and ("message" in t or "text" in t):
        for pattern in [
            r"message\s+(.+?)\s+on\s+whatsapp\s*[:\-]?\s*(.*)",
            r"text\s+(.+?)\s+on\s+whatsapp\s*[:\-]?\s*(.*)",
            r"whatsapp\s+message\s+to\s+(.+?)\s*[:\-]\s*(.*)",
        ]:
            m = re.search(pattern, t, re.IGNORECASE | re.DOTALL)
            if m:
                contact = m.group(1).strip()
                msg = (m.group(2) if m.lastindex >= 2 else "").strip()
                if contact:
                    return {"type": "tool", "tool": message_whatsapp, "args": {"contact": contact, "message": msg or ""}}

    # ---------- WHATSAPP: CALL ----------
    if "whatsapp" in t and "call" in t:
        m = re.search(r"call\s+(.+?)\s+on\s+whatsapp", t, re.IGNORECASE)
        if m:
            contact = m.group(1).strip()
            if contact:
                return {"type": "tool", "tool": call_whatsapp, "args": {"contact": contact}}

    # ---------- WECHAT: MESSAGE / TEXT ----------
    if "wechat" in t and ("message" in t or "text" in t):
        for pattern in [
            r"message\s+(.+?)\s+on\s+wechat\s*[:\-]?\s*(.*)",
            r"text\s+(.+?)\s+on\s+wechat\s*[:\-]?\s*(.*)",
            r"wechat\s+message\s+to\s+(.+?)\s*[:\-]\s*(.*)",
        ]:
            m = re.search(pattern, t, re.IGNORECASE | re.DOTALL)
            if m:
                contact = m.group(1).strip()
                msg = (m.group(2) if m.lastindex >= 2 else "").strip()
                if contact:
                    return {"type": "tool", "tool": message_wechat, "args": {"contact": contact, "message": msg or ""}}

    # ---------- WECHAT: CALL ----------
    if "wechat" in t and "call" in t:
        m = re.search(r"call\s+(.+?)\s+on\s+wechat", t, re.IGNORECASE)
        if m:
            contact = m.group(1).strip()
            if contact:
                return {"type": "tool", "tool": call_wechat, "args": {"contact": contact}}

    # ---------- PROTON VPN: CONNECT ----------
    if "proton vpn" in t or "protonvpn" in t:
        if "disconnect" in t:
            return {"type": "tool", "tool": vpn_disconnect_proton, "args": {}}
        for pattern in [
            r"connect\s+to\s+(.+?)\s+on\s+proton\s*vpn",
            r"proton\s*vpn\s+connect\s+to\s+(.+?)",
            r"proton\s*vpn\s+(.+?)\s*$",
        ]:
            m = re.search(pattern, t, re.IGNORECASE)
            if m:
                country = m.group(1).strip()
                if country and "disconnect" not in country:
                    return {"type": "tool", "tool": vpn_connect_proton, "args": {"country": country}}

    # ---------- HIDE.ME VPN: CONNECT / DISCONNECT ----------
    if "hide.me" in t or "hide me" in t or "hideme" in t:
        if "disconnect" in t:
            return {"type": "tool", "tool": vpn_disconnect_hideme, "args": {}}
        m = re.search(r"connect\s+to\s+(.+?)\s+on\s+hide\.?me", t, re.IGNORECASE)
        if m:
            return {"type": "tool", "tool": vpn_connect_hideme, "args": {"country": m.group(1).strip()}}
        m = re.search(r"hide\.?me\s+vpn\s+(.+?)\s*$", t, re.IGNORECASE)
        if m:
            country = m.group(1).strip()
            if country and "disconnect" not in country:
                return {"type": "tool", "tool": vpn_connect_hideme, "args": {"country": country}}

    # ---------- DEFAULT ----------
    return {
        "type": "chat",
        "reply": "Offline mode: try 'open <app>', 'write in notepad: <text>', 'message <name> on WhatsApp: <text>', 'call <name> on WhatsApp', 'connect to <country> on Proton VPN', 'play <song>', 'time', 'notes', 'timer'.",
    }