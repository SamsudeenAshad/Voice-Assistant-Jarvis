#!/usr/bin/env python
"""TTS with piper - local, offline. Downloads voice on first run if missing."""
import sys, subprocess, os, tempfile, argparse

# Default voice: en_US-lessac-medium (MIT)
VOICE = "en_US-lessac-medium"
MODEL_DIR = os.path.expanduser("~/.local/share/piper-voices")

def ensure_voice():
    # piper will auto-download if not present via piper.download_voices?
    # Fallback: use piper-tts CLI
    return VOICE

def speak(text):
    if not text.strip():
        return
    print(f"[TTS] {text}", file=sys.stderr)
    voice = ensure_voice()
    # Try piper CLI
    try:
        # Use piper binary if available: `piper --model <path> --output_file -`
        # Simpler: use python -m piper
        import piper
        # Use subprocess: echo text | piper --model <voice>.onnx --output_file -
        # For now use edge fallback if piper voice missing: use winsound + print
        # Attempt direct piper synthesis
        from piper.voice import PiperVoice
        import sounddevice as sd
        import soundfile as sf
        import tempfile
        # Find voice model
        voice_path = None
        for root,dirs,files in os.walk(os.path.expanduser(r"C:\Users\HP\.local\share\piper")):
            for f in files:
                if f.endswith(".onnx") and VOICE in f:
                    voice_path = os.path.join(root,f)
        if not voice_path:
            # Try default install location
            for p in [os.path.join(MODEL_DIR, f"{VOICE}.onnx"), f"{VOICE}.onnx"]:
                if os.path.exists(p):
                    voice_path = p; break
        if voice_path and os.path.exists(voice_path):
            v = PiperVoice.load(voice_path)
            # Synthesize to wav in memory and play
            import io, wave
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                with wave.open(tmp.name, 'wb') as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(v.config.sample_rate)
                    for chunk in v.synthesize(text):
                        wf.writeframes(chunk.audio_int16_bytes)
                data, sr = sf.read(tmp.name)
                sd.play(data, sr); sd.wait()
                os.unlink(tmp.name)
            return
        raise FileNotFoundError(f"voice {VOICE} not found at {voice_path}")
    except Exception as e:
        print(f"[TTS] piper failed ({e}), falling back to print + winsound", file=sys.stderr)
        # Fallback: Windows SAPI
        try:
            import subprocess
            ps_cmd = f'Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak("{text.replace(chr(34),chr(39))}");'
            subprocess.run(["powershell","-Command", ps_cmd], timeout=15)
        except Exception as e2:
            print(f"[TTS fallback failed {e2}]", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*", help="text to speak")
    parser.add_argument("--file", help="file with text")
    args = parser.parse_args()
    text = " ".join(args.text) if args.text else ""
    if args.file:
        text = open(args.file, encoding="utf-8").read()
    if not text:
        text = sys.stdin.read()
    speak(text)
