#!/usr/bin/env python
"""STT with faster-whisper - local, offline"""
import sys, os, argparse
import sounddevice as sd
import numpy as np
import tempfile, wave

# Use small model for speed - downloads on first run
MODEL = "small"  # or "base" for Gemma-level speed
SAMPLE_RATE = 16000

def record_until_silence(duration=8, silence_thresh=0.02, silence_duration=1.0):
    print(f"[STT] Listening {duration}s (speak now)...", file=sys.stderr)
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    # Trim silence at end but keep full for whisper
    return audio.flatten()

def transcribe(audio):
    from faster_whisper import WhisperModel
    # Use int8 for CPU speed
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    # Save to temp wav for whisper
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    # Write wav
    with wave.open(tmp, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())
    segments, info = model.transcribe(tmp, language="en", beam_size=5, vad_filter=True)
    text = " ".join(s.text for s in segments).strip()
    os.unlink(tmp)
    return text

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=8)
    args = parser.parse_args()
    audio = record_until_silence(duration=args.duration)
    text = transcribe(audio)
    print(text)
    print(f"[STT] -> {text}", file=sys.stderr)
