import sounddevice as sd
import numpy as np
import queue

INPUT_DEVICE = 15  # your mic array (WASAPI)
q = queue.Queue()

device_info = sd.query_devices(INPUT_DEVICE)
sr = int(device_info["default_samplerate"])
print("Using device:", device_info["name"])
print("Sample rate:", sr)

def callback(indata, frames, time, status):
    if status:
        print("Status:", status)
    q.put(indata.copy())

seconds = 3
frames_total = int(seconds * sr)
chunks = []

print(f"\nRecording {seconds}s... speak loudly now 🔥")

with sd.InputStream(device=INPUT_DEVICE, channels=1, samplerate=sr, callback=callback):
    collected = 0
    while collected < frames_total:
        data = q.get()
        chunks.append(data)
        collected += len(data)

audio = np.concatenate(chunks, axis=0)
peak = float(np.max(np.abs(audio)))

print("Peak volume:", peak)
print("✅ Done.")
