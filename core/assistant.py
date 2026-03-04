# core/assistant.py

from core.router import route
from core.memory import Memory
from core.telemetry import start_telemetry
from voice.tts import speak
from voice.stt import listen
from ui.ws_bridge import start_ws_server, broadcast


def jarvis_say(text: str, important: bool = False):
    """
    Only adds 'Master Mike' on important messages (startup/errors/shutdown/restart).
    Normal replies stay clean.
    """
    broadcast({"type": "status", "state": "speaking"})
    if important:
        speak(f"Master Mike, {text}", force_name=True)
    else:
        speak(text)


class Jarvis:
    def __init__(self):
        self.memory = Memory()

        # Start WebSocket bridge for the HUD
        start_ws_server()
        broadcast({"type": "status", "state": "online"})
        start_telemetry()

        jarvis_say("Jarvis online. Say 'Jarvis' to begin.", important=True)

    def run(self):
        while True:
            broadcast({"type": "status", "state": "listening"})
            text = listen()
            if not text:
                continue

            broadcast({"type": "heard", "text": text})
            t = text.lower().strip()

            # Shutdown phrases
            if any(phrase in t for phrase in [
                "shutdown jarvis", "shut down jarvis", "stop jarvis",
                "terminate jarvis", "goodbye jarvis", "bye jarvis",
                "exit", "quit",
            ]):
                jarvis_say("Shutting down. Goodbye.", important=True)
                broadcast({"type": "status", "state": "offline"})
                break

            # Restart phrases
            if any(phrase in t for phrase in ["restart jarvis", "reboot jarvis", "reload jarvis"]):
                jarvis_say("Restarting. Back online in a moment.", important=True)
                broadcast({"type": "status", "state": "restarting"})
                self.memory = Memory()
                continue

            # Wake-word handling: allow "Jarvis, ..." and "Jarvis" ping
            normalized = t.replace("jarvis,", "jarvis").replace("jarvis.", "jarvis")
            if normalized in ("jarvis", "hey jarvis"):
                jarvis_say("Yes?", important=False)
                continue

            if normalized.startswith("jarvis"):
                # Strip leading "Jarvis ..." from the command while preserving original casing
                parts = text.split(None, 1)
                if len(parts) == 2:
                    text = parts[1].strip()
                    t = text.lower().strip()

            # Route
            try:
                broadcast({"type": "status", "state": "routing"})
                action = route(text)
            except Exception as e:
                err = f"Router error: {e}"
                print(err)
                jarvis_say("Something went wrong routing that request.", important=True)
                broadcast({"type": "error", "message": err})
                self.memory.save(text, err)
                continue

            # Execute
            try:
                if action.get("type") == "tool":
                    tool_fn = action.get("tool")
                    args = action.get("args", {}) or {}

                    broadcast({
                        "type": "status",
                        "state": "executing",
                        "tool": getattr(tool_fn, "__name__", "tool")
                    })

                    if not callable(tool_fn):
                        raise TypeError("Action tool is not callable.")

                    result = tool_fn(**args)
                    result = "Done." if result is None else str(result)

                    jarvis_say(result, important=False)
                    broadcast({"type": "result", "text": result})
                    self.memory.save(text, result)

                else:
                    reply = action.get("reply") if isinstance(action, dict) else None
                    if not reply:
                        reply = "Offline mode: I can run commands like open apps, time, notes, search, timers."
                    reply = str(reply)

                    jarvis_say(reply, important=False)
                    broadcast({"type": "result", "text": reply})
                    self.memory.save(text, reply)

            except Exception as e:
                err = f"Execution error: {e}"
                print(err)
                jarvis_say("I hit an error running that. Check the console.", important=True)
                broadcast({"type": "error", "message": err})
                self.memory.save(text, err)