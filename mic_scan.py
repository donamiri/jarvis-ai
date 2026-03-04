import sounddevice as sd
import numpy as np
import queue

CANDIDATES = [15, 14, 20, 7, 1, 2, 8]  # from your list

def peak_for_device(dev_index, seconds=2):
    q = queue.Queue()
    dev = sd.query_devices(dev_index)
    sr = int(dev["default_samplerate"])

    def cb(indata, frames, time, status):
        q.put(indata.copy())

    frames_total = int(seconds * sr)
    chunks = []
    collected = 0

    try:
        with sd.InputStream(device=dev_index, channels=1, samplerate=sr, callback=cb):
            while collected < frames_total:
                data = q.get()
                chunks.append(data)
                collected += len(data)
    except Exception as e:
        return None, f"ERR: {e}"

    audio = np.concatenate(chunks, axis=0)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    return peak, None

print("Speak normally while this runs...\n")
for d in CANDIDATES:
    info = sd.query_devices(d)
    peak, err = peak_for_device(d)
    name = info["name"]
    if err:
        print(f"{d:>2} | {name[:55]:55} | {err}")
    else:
        print(f"{d:>2} | {name[:55]:55} | peak={peak:.6f}")