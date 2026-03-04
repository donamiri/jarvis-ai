import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SCOPES = "user-modify-playback-state user-read-playback-state"

def _client() -> spotipy.Spotify:
    cid = os.getenv("SPOTIFY_CLIENT_ID")
    secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect = os.getenv("SPOTIFY_REDIRECT_URI")

    if not cid or not secret or not redirect:
        raise RuntimeError("Missing Spotify env vars in .env")

    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=cid,
            client_secret=secret,
            redirect_uri=redirect,
            scope=SCOPES,
            open_browser=True,
            cache_path=".spotify_cache",
        )
    )

def _active_device_id(sp: spotipy.Spotify) -> str | None:
    devices = sp.devices().get("devices", [])
    if not devices:
        return None
    active = next((d for d in devices if d.get("is_active")), None)
    return (active or devices[0]).get("id")

def spotify_play(query: str) -> str:
    sp = _client()
    q = (query or "").strip()
    if not q:
        return "Tell me what to play."

    res = sp.search(q=q, type="track", limit=1)
    items = res.get("tracks", {}).get("items", [])
    if not items:
        return f"I couldn't find '{q}'."

    track = items[0]
    device_id = _active_device_id(sp)
    if not device_id:
        return "Open Spotify on your PC/phone and start playing something once, then try again."

    sp.start_playback(device_id=device_id, uris=[track["uri"]])
    artist = track["artists"][0]["name"] if track.get("artists") else "Unknown"
    return f"Playing {track['name']} by {artist}."

def spotify_pause() -> str:
    sp = _client()
    device_id = _active_device_id(sp)
    if not device_id:
        return "No Spotify device found. Open Spotify first."
    sp.pause_playback(device_id=device_id)
    return "Paused."

def spotify_resume() -> str:
    sp = _client()
    device_id = _active_device_id(sp)
    if not device_id:
        return "No Spotify device found. Open Spotify first."
    sp.start_playback(device_id=device_id)
    return "Resumed."

def spotify_next() -> str:
    sp = _client()
    device_id = _active_device_id(sp)
    if not device_id:
        return "No Spotify device found. Open Spotify first."
    sp.next_track(device_id=device_id)
    return "Next track."

def spotify_volume(percent: int) -> str:
    sp = _client()
    device_id = _active_device_id(sp)
    if not device_id:
        return "No Spotify device found. Open Spotify first."
    p = max(0, min(100, int(percent)))
    sp.volume(p, device_id=device_id)
    return f"Volume set to {p}%."