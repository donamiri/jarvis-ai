# skills/timer.py
import time

def set_timer(seconds: int) -> str:
    seconds = int(seconds)
    if seconds <= 0:
        return "Timer duration must be greater than zero."

    # Simple blocking timer (easy MVP)
    time.sleep(seconds)
    return f"Timer done: {seconds} seconds."
