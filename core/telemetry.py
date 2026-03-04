import threading
import time
from datetime import datetime
from typing import List, Optional

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None  # type: ignore

from ui.ws_bridge import broadcast


def _get_cpu_mem() -> tuple[Optional[float], Optional[float]]:
    cpu = None
    mem = None
    if psutil is None:
        return cpu, mem

    try:
        cpu = float(psutil.cpu_percent(interval=0.0))
        mem = float(psutil.virtual_memory().percent)
    except Exception:
        pass
    return cpu, mem


def _get_online() -> Optional[bool]:
    if psutil is None:
        return None
    try:
        stats = psutil.net_if_stats()
        if not stats:
            return None
        return any(s.isup for s in stats.values())
    except Exception:
        return None


def _get_top_apps(limit: int = 4) -> List[str]:
    if psutil is None:
        return []

    apps: List[tuple[float, str]] = []
    try:
        for proc in psutil.process_iter(["name", "cpu_percent"]):
            name = proc.info.get("name") or ""
            cpu = float(proc.info.get("cpu_percent") or 0.0)
            if not name:
                continue
            apps.append((cpu, name))
    except Exception:
        return []

    # Sort by CPU usage, highest first, and dedupe by name
    apps.sort(reverse=True)
    seen = set()
    result: List[str] = []

    for cpu, name in apps:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        label = f"{name} ({cpu:.0f}%)" if cpu else name
        result.append(label)
        if len(result) >= limit:
            break

    return result


def _loop() -> None:
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        cpu, mem = _get_cpu_mem()
        online = _get_online()
        apps = _get_top_apps()

        payload = {
            "type": "telemetry",
            "time": now,
            "cpu": cpu,
            "mem": mem,
            "online": online,
            "apps": apps,
        }
        broadcast(payload)
        time.sleep(1.0)


def start_telemetry() -> None:
    t = threading.Thread(target=_loop, daemon=True)
    t.start()

