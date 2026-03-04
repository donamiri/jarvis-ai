import asyncio
import json
import threading
from typing import Set

import websockets
from websockets.server import WebSocketServerProtocol

from voice.stt import inject_command, start_voice_capture

_clients: Set[WebSocketServerProtocol] = set()

def start_ws_server(host="127.0.0.1", port=8765):
    def _run():
        asyncio.run(_main(host, port))
    threading.Thread(target=_run, daemon=True).start()

async def _handler(ws: WebSocketServerProtocol):
    _clients.add(ws)
    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
            except Exception:
                continue

            if data.get("type") == "command":
                inject_command(data.get("text", ""))

            if data.get("type") == "voice":
                start_voice_capture()

    finally:
        _clients.discard(ws)

async def _main(host, port):
    async with websockets.serve(_handler, host, port):
        await asyncio.Future()

def broadcast(event: dict):
    payload = json.dumps(event)

    async def _send_all():
        dead = []
        for ws in list(_clients):
            try:
                await ws.send(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _clients.discard(ws)

    def _kick():
        try:
            asyncio.run(_send_all())
        except Exception:
            pass

    threading.Thread(target=_kick, daemon=True).start()