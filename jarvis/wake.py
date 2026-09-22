#!/usr/bin/env python
"""Wake word - simple 'jarvis' detection via whisper small + energy, or openWakeWord"""
import sys
# Lightweight fallback: just listen for 3s and check if 'jarvis' in transcription
# Replace with openWakeWord for always-on
import sounddevice as sd
import numpy as np
import tempfile, wave, os

SAMPLE_RATE = 16000

def listen_for_wake(word="jarvis", timeout=30):
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    print(f"[WAKE] Waiting for '{word}'... (say '{word}' or say 'hey jarvis')", file=sys.stderr)
    import time
    start = time.time()
    while time.time() - start < timeout:
        # Record 3s window
        audio = sd.rec(int(3 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        # VAD: skip silence
        if np.abs(audio).mean() < 0.01:
            continue
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        with wave.open(tmp, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
            wf.writeframes((audio.flatten() * 32767).astype(np.int16).tobytes())
        segments, _ = model.transcribe(tmp, language="en", beam_size=1, vad_filter=True)
        text = " ".join(s.text for s in segments).lower()
        os.unlink(tmp)
        print(f"[WAKE] heard: {text}", file=sys.stderr)
        if word in text or "hey" in text:
            return True
    return False

if __name__ == "__main__":
    ok = listen_for_wake()
    print("WAKE" if ok else "TIMEOUT")
