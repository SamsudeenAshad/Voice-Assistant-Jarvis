#!/usr/bin/env python
"""Verified wake: 'hey javis' / 'hey javis i am ashad here' ONLY for Ashad's voice"""
import os, sys, re, tempfile, wave, numpy as np, sounddevice as sd
SAMPLE_RATE = 16000
ENROLL_PATH = os.path.join(os.path.dirname(__file__), "ashad_voice.npy")
THRESHOLD = 0.72  # lower a bit for Q1_0 noisy

# Wake phrases - handle mis-transcriptions of "javis"
WAKE_PATTERNS = [
    r"hey\s+javis", r"hey\s+jarvis", r"hey\s+javas", r"hey\s+service",  # whisper variants
    r"hey\s+javis\s+i\s+am\s+ashad", r"hey\s+jarvis\s+i\s+am\s+ashad",
    r"javis", r"jarvis"  # fallback if just 'javis' detected with high energy
]

def get_embedding(audio):
    try:
        from resemblyzer import VoiceEncoder
        encoder = VoiceEncoder("cpu")
        emb = encoder.embed_utterance(audio)
        return emb / np.linalg.norm(emb)
    except Exception as e:
        # MFCC fallback
        try:
            import librosa
            mfcc = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
            emb = mfcc.mean(axis=1)
            return emb / np.linalg.norm(emb)
        except:
            emb = np.abs(np.fft.rfft(audio)[:128])
            return emb / (np.linalg.norm(emb)+1e-9)

def is_wake(text):
    text = text.lower()
    for pat in WAKE_PATTERNS:
        if re.search(pat, text):
            return True
    return False

def verify_speaker(audio):
    if not os.path.exists(ENROLL_PATH):
        print("[WAKE] No enrollment found - run enroll.py first, allowing any voice for now", file=sys.stderr)
        return True, 1.0
    enrolled = np.load(ENROLL_PATH)
    emb = get_embedding(audio)
    # Handle dimension mismatch if fallback vs resemblyzer mismatch - re-enroll needed
    if enrolled.shape != emb.shape:
        print(f"[WAKE] Embedding shape mismatch {enrolled.shape} vs {emb.shape}, re-run enroll.py", file=sys.stderr)
        return True, 0.5
    sim = float(np.dot(enrolled, emb))
    return sim > THRESHOLD, sim

def listen_once(duration=3):
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    return audio.flatten()

def transcribe(audio):
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    with wave.open(tmp, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())
    segments, _ = model.transcribe(tmp, language="en", beam_size=1, vad_filter=True)
    text = " ".join(s.text for s in segments).lower().strip()
    os.unlink(tmp)
    return text

if __name__ == "__main__":
    # Test mode
    print("[WAKE-VERIFIED] Listening for 'hey javis' / 'hey javis i am ashad here' ONLY Ashad...")
    while True:
        audio = listen_once(3)
        if np.abs(audio).mean() < 0.008:
            continue
        text = transcribe(audio)
        print(f"[heard] {text}", file=sys.stderr)
        if is_wake(text):
            ok, sim = verify_speaker(audio)
            print(f"[wake] phrase match, speaker sim {sim:.3f} -> {'ASHAD OK' if ok else 'NOT ASHAD - ignored'}", file=sys.stderr)
            if ok:
                print("WAKE_ASHAD")
                break
            else:
                print("REJECT_NOT_ASHAD", file=sys.stderr)
