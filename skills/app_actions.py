# skills/app_actions.py
# In-app actions for indexed apps: type text, message/call (WhatsApp/WeChat), VPN connect.
# Uses UI automation (pyautogui) and, where available, CLI (Proton VPN).

import re
import subprocess
import time
from typing import Optional

from skills.system import open_app
from skills.app_indexer import load_index, build_index

# Optional: UI automation. If not installed, in-app typing/messaging will be disabled.
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.15
    _HAS_PYAUTOGUI = True
except ImportError:
    _HAS_PYAUTOGUI = False

# Optional: focus window by title on Windows
try:
    import pygetwindow as gw
    _HAS_PYGETWINDOW = True
except ImportError:
    _HAS_PYGETWINDOW = False


def _focus_window(title_substring: str, wait_sec: float = 3.0) -> bool:
    """Try to bring a window whose title contains title_substring to the front."""
    if not _HAS_PYGETWINDOW or not title_substring:
        return False
    title_sub = title_substring.lower()
    for _ in range(int(wait_sec * 10)):
        try:
            for w in gw.getAllWindows():
                if w.title and title_sub in w.title.lower():
                    try:
                        w.activate()
                        return True
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(0.1)
    return False


def _type_text(text: str, use_clipboard: bool = True) -> None:
    """Type text. If use_clipboard, paste via Ctrl+V to support unicode/special chars."""
    if not _HAS_PYAUTOGUI:
        return
    if use_clipboard and text:
        try:
            import pyperclip
            old = pyperclip.paste()
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
            try:
                pyperclip.copy(old)
            except Exception:
                pass
        except ImportError:
            pyautogui.write(text, interval=0.05)
        except Exception:
            pyautogui.write(text, interval=0.05)
    else:
        pyautogui.write(text, interval=0.05)


# ----- Notepad / generic "type in app" -----

def type_in_app(app_name: str, text: str) -> str:
    """
    Open an indexed app (e.g. notepad, word) and type the given text.
    Works with any app that accepts keyboard input after opening.
    """
    if not _HAS_PYAUTOGUI:
        return "Install pyautogui for in-app typing: pip install pyautogui"

    text = (text or "").strip()
    if not text:
        return "No text to type."

    # Open app using existing index/aliases
    open_app(app_name)
    time.sleep(2.0)

    # Try to focus by common window titles
    if app_name.lower() in ("notepad", "notepad.exe"):
        _focus_window("Notepad") or _focus_window("Untitled")
    elif "word" in app_name.lower():
        _focus_window("Word") or _focus_window("Document")
    else:
        _focus_window(app_name.split()[-1] if app_name else "")

    time.sleep(0.3)
    _type_text(text, use_clipboard=True)
    return f"Typed into {app_name}."
    # If you use notepad, add newline:
    # pyautogui.press("enter")


def write_in_notepad(text: str) -> str:
    """Convenience: open Notepad and type text."""
    return type_in_app("notepad", text)


# ----- WhatsApp (desktop or web) -----

def message_whatsapp(contact: str, message: str) -> str:
    """
    Open WhatsApp, search for contact, and type message.
    Requires WhatsApp Desktop or browser on web.whatsapp.com; window must be visible.
    """
    if not _HAS_PYAUTOGUI:
        return "Install pyautogui for WhatsApp automation: pip install pyautogui"

    contact = (contact or "").strip()
    message = (message or "").strip()
    if not contact:
        return "Say who to message, e.g. 'message John on WhatsApp: hello'."

    open_app("whatsapp")
    time.sleep(3.0)
    _focus_window("WhatsApp")
    time.sleep(0.5)
    # Search: Ctrl+F or click search box; then type contact name
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.8)
    _type_text(contact, use_clipboard=True)
    time.sleep(1.2)
    pyautogui.press("enter")
    time.sleep(0.8)
    if message:
        _type_text(message, use_clipboard=True)
        pyautogui.press("enter")
    return f"Opened WhatsApp, searched for '{contact}' and sent the message."
    # Note: "Call X on WhatsApp" can be done by opening chat then triggering call (e.g. click call icon); 
    # we can add call_whatsapp(contact) that does Enter then hotkey or image-based click if needed.


def call_whatsapp(contact: str) -> str:
    """Open WhatsApp, search contact, open chat. User can press call or we send Enter then try to trigger call."""
    if not _HAS_PYAUTOGUI:
        return "Install pyautogui for WhatsApp automation."
    contact = (contact or "").strip()
    if not contact:
        return "Say who to call, e.g. 'call John on WhatsApp'."
    open_app("whatsapp")
    time.sleep(3.0)
    _focus_window("WhatsApp")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.8)
    _type_text(contact, use_clipboard=True)
    time.sleep(1.2)
    pyautogui.press("enter")
    time.sleep(0.5)
    # Optional: trigger voice call (often Ctrl+Shift+C or a specific shortcut; app-dependent)
    # pyautogui.hotkey("ctrl", "shift", "c")
    return f"Opened WhatsApp chat with '{contact}'. You can start the call from the window."


# ----- WeChat -----

def message_wechat(contact: str, message: str) -> str:
    """Open WeChat, search for contact, type message. Requires WeChat desktop window visible."""
    if not _HAS_PYAUTOGUI:
        return "Install pyautogui for WeChat automation: pip install pyautogui"

    contact = (contact or "").strip()
    message = (message or "").strip()
    if not contact:
        return "Say who to message, e.g. 'message John on WeChat: hello'."

    open_app("wechat")
    time.sleep(3.0)
    _focus_window("WeChat")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.8)
    _type_text(contact, use_clipboard=True)
    time.sleep(1.2)
    pyautogui.press("enter")
    time.sleep(0.8)
    if message:
        _type_text(message, use_clipboard=True)
        pyautogui.press("enter")
    return f"Opened WeChat, searched for '{contact}' and sent the message."


def call_wechat(contact: str) -> str:
    """Open WeChat and open chat with contact; user can start call."""
    if not _HAS_PYAUTOGUI:
        return "Install pyautogui for WeChat automation."
    contact = (contact or "").strip()
    if not contact:
        return "Say who to call, e.g. 'call John on WeChat'."
    open_app("wechat")
    time.sleep(3.0)
    _focus_window("WeChat")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.8)
    _type_text(contact, use_clipboard=True)
    time.sleep(1.2)
    pyautogui.press("enter")
    return f"Opened WeChat chat with '{contact}'. You can start the call from the window."


# ----- Proton VPN (CLI if available) -----

PROTONVPN_COUNTRY_CODES = {
    "us": "US", "usa": "US", "united states": "US", "america": "US",
    "uk": "GB", "britain": "GB", "united kingdom": "GB",
    "de": "DE", "germany": "DE",
    "fr": "FR", "france": "FR",
    "nl": "NL", "netherlands": "NL", "holland": "NL",
    "jp": "JP", "japan": "JP",
    "sg": "SG", "singapore": "SG",
    "au": "AU", "australia": "AU",
    "ca": "CA", "canada": "CA",
    "in": "IN", "india": "IN",
    "br": "BR", "brazil": "BR",
    "ch": "CH", "switzerland": "CH",
    "se": "SE", "sweden": "SE",
    "no": "NO", "norway": "NO",
    "es": "ES", "spain": "ES",
    "it": "IT", "italy": "IT",
    "kr": "KR", "korea": "KR", "south korea": "KR",
    "hk": "HK", "hong kong": "HK",
    "tw": "TW", "taiwan": "TW",
}


def _normalize_country(country: str) -> Optional[str]:
    c = country.lower().strip()
    return PROTONVPN_COUNTRY_CODES.get(c) or PROTONVPN_COUNTRY_CODES.get(c.replace(" ", ""))


def vpn_connect_proton(country: str) -> str:
    """
    Connect Proton VPN to a country. Uses Proton VPN CLI if installed (e.g. protonvpn-cli connect DE).
    On Windows, CLI may be installed separately; otherwise we could fall back to opening the app (no automation).
    """
    code = _normalize_country(country)
    if not code:
        return f"Unknown country '{country}'. Try: US, UK, Germany, Japan, Netherlands, etc."
    for exe in ("protonvpn-cli", "protonvpn-cli.exe", "pvpn-cli"):
        try:
            out = subprocess.run(
                [exe, "connect", code],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if out.returncode == 0:
                return f"Proton VPN connecting to {country} ({code})."
            if "already connected" in (out.stderr or "").lower() or "already connected" in (out.stdout or "").lower():
                return f"Proton VPN is already connected. Disconnect first if you want to switch to {country}."
            return f"Proton VPN CLI: {out.stderr or out.stdout or 'failed'}."
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            return "Proton VPN connection timed out."
    # Fallback: open Proton VPN app; user selects country manually
    open_app("proton vpn")
    return f"Proton VPN app opened. Select {country} manually, or install Proton VPN CLI for voice control."


def vpn_disconnect_proton() -> str:
    try:
        for exe in ("protonvpn-cli", "protonvpn-cli.exe", "pvpn-cli"):
            try:
                subprocess.run([exe, "disconnect"], capture_output=True, timeout=15)
                return "Proton VPN disconnecting."
            except FileNotFoundError:
                continue
    except Exception:
        pass
    open_app("proton vpn")
    return "Proton VPN app opened. Disconnect manually if CLI is not installed."


# ----- Hide.me VPN (no CLI; use UI automation) -----

def vpn_connect_hideme(country: str) -> str:
    """
    Open Hide.me VPN and try to connect to country via keyboard (search box + Enter).
    UI layout may vary; this is a best-effort automation.
    """
    if not _HAS_PYAUTOGUI:
        open_app("hide.me vpn")
        return f"Hide.me VPN opened. Select {country} manually. Install pyautogui for automatic connection."

    open_app("hide.me vpn")
    time.sleep(4.0)
    _focus_window("hide.me") or _focus_window("HideMe") or _focus_window("VPN")
    time.sleep(0.5)
    # Many VPN UIs: click in search or country list, type country, Enter
    _type_text(country, use_clipboard=True)
    time.sleep(0.8)
    pyautogui.press("enter")
    time.sleep(0.5)
    # Sometimes double Enter or Tab to "Connect"
    pyautogui.press("enter")
    return f"Hide.me VPN: opened and attempted to select {country}. Check the app and connect if needed."


def vpn_disconnect_hideme() -> str:
    if not _HAS_PYAUTOGUI:
        open_app("hide.me vpn")
        return "Hide.me VPN opened. Disconnect manually."
    open_app("hide.me vpn")
    time.sleep(3.0)
    _focus_window("hide.me") or _focus_window("HideMe")
    time.sleep(0.3)
    # Common: Escape or a "Disconnect" button; try Escape
    pyautogui.press("escape")
    time.sleep(0.2)
    pyautogui.press("escape")
    return "Hide.me VPN: disconnect attempted. Check the app."


# ----- Generic "type in any indexed app" -----

def type_in_indexed_app(app_name: str, text: str) -> str:
    """
    Resolve app_name against the indexed apps (apps.json), open it, and type text.
    Use for any app in your Start Menu index (e.g. "word", "excel", "notepad").
    """
    apps = load_index()
    if not apps:
        apps = build_index()
    name_lower = (app_name or "").lower().strip()
    if name_lower in apps:
        return type_in_app(app_name, text)
    from difflib import get_close_matches
    candidates = get_close_matches(name_lower, [k.lower() for k in apps.keys()], n=3, cutoff=0.5)
    if candidates:
        # Restore original key from index
        for k in apps:
            if k.lower() == candidates[0]:
                return type_in_app(k, text)
    return f"App '{app_name}' not found in index. Try 'reindex apps' or use exact name from the list."
