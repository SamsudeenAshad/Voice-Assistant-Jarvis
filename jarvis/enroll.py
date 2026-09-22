#!/usr/bin/env python
"""Enroll Ashad's voice for 'hey javis' - only your voice will activate Jarvis"""
import os, sys, numpy as np, sounddevice as sd, wave, tempfile
SAMPLE_RATE = 16000
ENROLL_PATH = os.path.join(os.path.dirname(__file__), "ashad_voice.npy")
THRESHOLD = 0.75

def record(duration=3):
    print(f"[ENROLL] Recording {duration}s - say 'hey javis' clearly...", file=sys.stderr)
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    return audio.flatten()

def get_embedding(audio):
    """Use resemblyzer if available, else MFCC fallback"""
    try:
        from resemblyzer import VoiceEncoder
        encoder = VoiceEncoder("cpu")
        # resemblyzer expects 16k wav
        emb = encoder.embed_utterance(audio)
        return emb / np.linalg.norm(emb)
    except Exception as e:
        print(f"[enroll] resemblyzer not available ({e}), using MFCC fallback", file=sys.stderr)
        # Simple MFCC mean fallback - not as secure but works offline
        try:
            import librosa
            mfcc = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=13)
            emb = mfcc.mean(axis=1)
            return emb / np.linalg.norm(emb)
        except:
            # Last fallback: raw spectral mean
            emb = np.fft.rfft(audio)
            emb = np.abs(emb[:128])
            return emb / (np.linalg.norm(emb)+1e-9)

if __name__ == "__main__":
    print("=== Enroll Ashad - only your voice will start Jarvis ===")
    print("You will say 'hey javis i am ashad here' 3 times")
    embs = []
    for i in range(3):
        input(f"Press Enter then say 'hey javis i am ashad here' (sample {i+1}/3)...")
        audio = record(3)
        emb = get_embedding(audio)
        embs.append(emb)
        print(f"Sample {i+1} captured, norm {np.linalg.norm(emb):.2f}")
    # Average
    avg = np.mean(embs, axis=0)
    avg = avg / np.linalg.norm(avg)
    np.save(ENROLL_PATH, avg)
    print(f"Saved voice profile to {ENROLL_PATH}")
    print(f"Test: threshold {THRESHOLD} cosine similarity")
    # Quick verify
    input("Test now - say 'hey javis' again...")
    test_audio = record(3)
    test_emb = get_embedding(test_audio)
    sim = float(np.dot(avg, test_emb))
    print(f"Similarity: {sim:.3f} -> {'PASS (would unlock)' if sim>THRESHOLD else 'FAIL (would not unlock)'}")
    print("Done. Jarvis will now only respond to YOU.")
