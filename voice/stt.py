# voice/stt.py
# Push-to-talk (V) + Manual typing (T) — terminal focused (stable)
# PLUS: Accept commands injected from HUD
# PLUS: HUD can trigger a voice capture (no terminal keypress)

import msvcrt
import queue
import time
import tempfile

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
from faster_whisper import WhisperModel

INPUT_DEVICE = 1  # your working mic index
MAX_SECONDS = 10
SILENCE_THRESHOLD = 0.01

model = WhisperModel("base", device="cpu", compute_type="int8")

INJECT_QUEUE: "queue.Queue[str]" = queue.Queue()
VOICE_TRIGGER = False  # HUD can flip this to start voice recording
VOICE_ONLY_MODE = True  # continuous voice-only mode (no keyboard needed)


def inject_command(text: str):
    text = (text or "").strip()
    if text:
        INJECT_QUEUE.put(text)


def start_voice_capture():
    global VOICE_TRIGGER
    VOICE_TRIGGER = True


def _record_audio(stop_on_v: bool = True):
    q = queue.Queue()
    dev = sd.query_devices(INPUT_DEVICE)
    sr = int(dev["default_samplerate"])

    def callback(indata, frames, time_info, status):
        q.put(indata.copy())

    chunks = []
    start = time.time()

    with sd.InputStream(device=INPUT_DEVICE, channels=1, samplerate=sr, callback=callback):
        if stop_on_v:
            print("🎙️ Speak now... (press V again to stop)")
        else:
            print(f"🎙️ Speak now... (auto-stops after {MAX_SECONDS}s)")

        while True:
            # Optional manual stop with V
            if stop_on_v and msvcrt.kbhit():
                key = msvcrt.getwch()
                if key.lower() == "v":
                    break

            if time.time() - start > MAX_SECONDS:
                break

            try:
                data = q.get(timeout=0.2)
                chunks.append(data)
            except queue.Empty:
                continue

    if not chunks:
        return None, None

    audio = np.concatenate(chunks, axis=0).astype(np.float32)
    peak = float(np.max(np.abs(audio)))

    if peak < SILENCE_THRESHOLD:
        print("⚠️ Too quiet.")
        return None, None

    audio = np.clip(audio * 2.0, -1.0, 1.0)
    audio_i16 = (audio * 32767).astype(np.int16)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    write(wav_path, sr, audio_i16)

    return wav_path, peak


def _transcribe(wav_path: str) -> str:
    print("🧠 Transcribing...")
    segments, _ = model.transcribe(wav_path, vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()


def listen() -> str:
    global VOICE_TRIGGER, VOICE_ONLY_MODE

    # 0) If HUD injected a normal command, run it immediately
    try:
        injected = INJECT_QUEUE.get_nowait()
        print(f"YOU (hud): {injected}")
        # User is effectively in typing/command mode: pause auto voice
        VOICE_ONLY_MODE = False
        return injected
    except queue.Empty:
        pass

    # 1) If HUD requested voice capture, record now (no keypress)
    if VOICE_TRIGGER:
        VOICE_TRIGGER = False
        wav_path, _ = _record_audio(stop_on_v=False)
        if not wav_path:
            return ""
        text = _transcribe(wav_path)
        print(f"YOU (voice/hud): {text}")
        VOICE_ONLY_MODE = True
        return text

    # 2) Voice-only mode: auto record + transcribe without keypress
    if VOICE_ONLY_MODE:
        wav_path, _ = _record_audio(stop_on_v=False)
        if not wav_path:
            return ""
        text = _transcribe(wav_path)
        print(f"YOU (voice/auto): {text}")
        VOICE_ONLY_MODE = True
        return text

    print("\n🟢 Standby — Press V to speak | Press T to type")

    while True:
        # Keep checking for HUD command injection
        try:
            injected = INJECT_QUEUE.get_nowait()
            print(f"YOU (hud): {injected}")
            return injected
        except queue.Empty:
            pass

        # Also allow HUD to trigger voice capture while waiting
        if VOICE_TRIGGER:
            VOICE_TRIGGER = False
            wav_path, _ = _record_audio(stop_on_v=False)
            if not wav_path:
                return ""
            text = _transcribe(wav_path)
            print(f"YOU (voice/hud): {text}")
            VOICE_ONLY_MODE = True
            return text

        if msvcrt.kbhit():
            key = msvcrt.getwch().lower()

            if key == "v":
                wav_path, _ = _record_audio(stop_on_v=True)
                if not wav_path:
                    return ""
                text = _transcribe(wav_path)
                print(f"YOU (voice): {text}")
                VOICE_ONLY_MODE = True
                return text

            if key == "t":
                # User explicitly chose typing: turn off auto voice until they next use voice
                VOICE_ONLY_MODE = False
                return input("YOU (type): ").strip()