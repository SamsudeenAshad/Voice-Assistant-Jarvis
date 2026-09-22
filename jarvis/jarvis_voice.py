#!/usr/bin/env python
"""
Jarvis - Local voice agent using LM Studio (Gemma 3 1B + Bonsai 27B) + OpenCode
Does: local conversation + task execution with approval before actions
Uses opencode CLI for session management (handles auth automatically)
"""
import subprocess, json, sys, os, time, threading, queue, re

OPCODE_DIR = r"D:\opencode"
LMSTUDIO_URL = "http://127.0.0.1:1234/v1/models"

def run_opencode_api(method, path, data=None):
    cmd = ["opencode", "api", method, path]
    if data is not None:
        cmd += ["--data", json.dumps(data)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=OPCODE_DIR)
    if result.returncode != 0:
        # Try to parse error
        print(f"[opencode api {method} {path} failed]\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}", file=sys.stderr)
        return None
    out = result.stdout.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except:
        print(out)
        return out

def check_lmstudio():
    import urllib.request
    try:
        with urllib.request.urlopen(LMSTUDIO_URL, timeout=3) as r:
            data = json.loads(r.read().decode())
            models = data.get("data", [])
            print(f"[LMStudio] Online: {[m['id'] for m in models]}")
            return models
    except Exception as e:
        print(f"[LMStudio] Not running at {LMSTUDIO_URL}: {e}\n -> Start LM Studio -> Local Server -> Start Server", file=sys.stderr)
        return None

def speak(text):
    # Use tts.py -> fallback to powershell SAPI if piper not installed
    try:
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "tts.py"), text], timeout=20)
    except Exception as e:
        print(f"[TTS] {text} (fallback: {e})")
        # Windows SAPI fallback inline
        try:
            ps = f'Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak("{text.replace(chr(34),chr(39))}");'
            subprocess.run(["powershell","-Command", ps], timeout=15)
        except: pass
        print(f"JARVIS: {text}")

def transcribe(duration=7):
    try:
        result = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "stt.py"), "--duration", str(duration)], capture_output=True, text=True, timeout=30)
        text = result.stdout.strip().split("\n")[-1] if result.stdout.strip() else ""
        # stt.py prints text to stdout last line
        if not text:
            print(f"[STT stderr] {result.stderr}", file=sys.stderr)
        return text
    except Exception as e:
        print(f"[STT failed {e}] falling back to keyboard", file=sys.stderr)
        return input("[YOU - type]: ").strip()

def check_approval_needed(session_id):
    # Poll for permission requests
    perms = run_opencode_api("get", f"/api/session/{session_id}/permission")
    if isinstance(perms, list) and perms:
        return perms[0]
    if isinstance(perms, dict) and perms.get("data"):
        lst = perms["data"]
        if lst: return lst[0]
    return None

# --- Main ---
if __name__ == "__main__":
    print("=== JARVIS Local (Gemma 3 1B + Bonsai 27B via LM Studio + OpenCode) ===")
    models = check_lmstudio()
    if not models:
        speak("My local brain is offline. Please start LM Studio server on port 1234.")
        # Continue anyway for testing

    # Create session
    print("[OpenCode] Creating session...")
    sess = run_opencode_api("post", "/api/session", {"directory": OPCODE_DIR})
    if not sess:
        print("Failed to create session - check D:\\opencode\\opencode.jsonc and opencode service", file=sys.stderr)
        sys.exit(1)
    session_id = sess.get("id") or sess.get("data",{}).get("id") or sess["id"] if isinstance(sess, dict) else None
    # run_opencode_api returns parsed JSON, which for POST /api/session is {id, ...}
    if isinstance(sess, dict) and "id" not in sess and "data" in sess:
        session_id = sess["data"]["id"]
    else:
        session_id = sess.get("id")
    print(f"[Session] {session_id}")
    speak("Jarvis online. Local models Gemma for chat, Bonsai for tasks. Say hey Jarvis, then your request. I will ask for approval before taking actions.")

    # Background poll for permissions
    def permission_watcher():
        while True:
            try:
                req = check_approval_needed(session_id)
                if req:
                    rid = req.get("id")
                    action = req.get("action")
                    resources = req.get("resources", [])
                    msg = req.get("message") or f"{action} {resources}"
                    print(f"\n[PERMISSION ASK] {msg} (id={rid})", file=sys.stderr)
                    speak(f"Should I run {action} on {', '.join(resources[:2])}? Say yes, always, or no.")
                    ans = transcribe(duration=5).lower()
                    if "always" in ans:
                        reply = "always"
                    elif "yes" in ans or "approve" in ans or "ok" in ans or "go ahead" in ans:
                        reply = "once"
                    else:
                        reply = "reject"
                    print(f"[PERMISSION REPLY] {reply} for {rid}", file=sys.stderr)
                    run_opencode_api("post", f"/api/session/{session_id}/permission/{rid}/reply", {"reply": reply})
                    speak("Approved." if reply!="reject" else "Denied.")
            except Exception as e:
                print(f"[perm watcher] {e}", file=sys.stderr)
            time.sleep(1.5)

    threading.Thread(target=permission_watcher, daemon=True).start()

    # Main voice loop - wake verified for Ashad only
    import re
    WAKE_PATTERNS = [r"hey\s+javis", r"hey\s+jarvis", r"javis", r"jarvis", r"hey\s+javis\s+i\s+am\s+ashad"]
    ENROLL_PATH = os.path.join(os.path.dirname(__file__), "ashad_voice.npy")
    THRESHOLD = 0.72

    def is_wake(text):
        t=text.lower()
        return any(re.search(p, t) for p in WAKE_PATTERNS)

    def verify_speaker(audio):
        if not os.path.exists(ENROLL_PATH):
            return True, 1.0  # no enrollment yet -> allow
        try:
            import numpy as np
            enrolled = np.load(ENROLL_PATH)
            # get embedding from wake audio
            try:
                from resemblyzer import VoiceEncoder
                enc = VoiceEncoder("cpu")
                emb = enc.embed_utterance(audio)
            except:
                import librosa
                mfcc = librosa.feature.mfcc(y=audio, sr=16000, n_mfcc=13)
                emb = mfcc.mean(axis=1)
            emb = emb/np.linalg.norm(emb)
            if enrolled.shape != emb.shape:
                return True, 0.5
            sim=float(np.dot(enrolled, emb))
            return sim>THRESHOLD, sim
        except Exception as e:
            print(f"[verify] {e}", file=sys.stderr)
            return True, 0.5

    def wait_for_wake():
        from faster_whisper import WhisperModel
        import sounddevice as sd, wave, tempfile, numpy as np
        model = WhisperModel("small", device="cpu", compute_type="int8")
        print("\n[WAKE] Waiting for 'hey javis' or 'hey javis i am ashad here' (Ashad only)...", file=sys.stderr)
        speak("Waiting for your voice, Ashad.")
        while True:
            audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='float32')
            sd.wait()
            if np.abs(audio).mean() < 0.008:
                continue
            flat = audio.flatten()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp=f.name
            with wave.open(tmp,'wb') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
                wf.writeframes((flat*32767).astype(np.int16).tobytes())
            segments,_ = model.transcribe(tmp, language="en", beam_size=1, vad_filter=True)
            text=" ".join(s.text for s in segments).lower().strip()
            os.unlink(tmp)
            if not text: continue
            print(f"[WAKE heard] {text}", file=sys.stderr)
            if is_wake(text):
                ok, sim = verify_speaker(flat)
                print(f"[WAKE] sim {sim:.3f} -> {'ASHAD' if ok else 'NOT ASHAD'}", file=sys.stderr)
                if ok:
                    speak("Yes Ashad?")
                    # If wake phrase included task, return remainder
                    # e.g. "hey javis create file" -> strip wake and return task
                    remainder = re.sub(r"^.*?(javis|jarvis)\s*", "", text, flags=re.I)
                    remainder = re.sub(r"i\s+am\s+ashad\s+here\s*", "", remainder, flags=re.I).strip()
                    return remainder  # may be "" if just wake, caller will listen again for command
                else:
                    speak("I only respond to Ashad.")
            # else ignore other voices / phrases

    while True:
        try:
            wake_remainder = wait_for_wake()
            # If wake included command, use it, else listen for command
            if wake_remainder and len(wake_remainder)>3:
                text = wake_remainder
                print(f"[WAKE+CMD] {text}")
            else:
                print("\n--- Listening for command (speak now) ---")
                text = transcribe(duration=7)
                if not text or len(text.strip()) < 2:
                    print("[heard nothing, retry]")
                    continue
            print(f"[YOU] {text}")
            if text.lower().strip() in ["exit","quit","goodbye javis","goodbye jarvis","stop"]:
                speak("Goodbye Ashad.")
                break
            # Strip wake word if still present
            text = re.sub(r"^\s*hey\s+javis[^a-z]*", "", text, flags=re.I)
            text = re.sub(r"^\s*hey\s+jarvis[^a-z]*", "", text, flags=re.I)
            text = re.sub(r"^\s*javis\s*", "", text, flags=re.I)
            text = re.sub(r"i\s+am\s+ashad\s+here\s*", "", text, flags=re.I).strip()
            if not text:
                continue

            # Send to OpenCode Bonsai
            print(f"[OpenCode] Prompting {session_id}...")
            # Use streaming prompt via API: POST /api/session/{id}/prompt
            # This will run until completion, permissions will be handled by watcher
            cmd = ["opencode", "api", "post", f"/api/session/{session_id}/prompt", "--data", json.dumps({"text": text})]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=OPCODE_DIR, bufsize=1)
            full = ""
            try:
                # Read stdout line by line (SSE or JSON)
                for line in proc.stdout:
                    line=line.strip()
                    if not line: continue
                    # Try parse as JSON event
                    try:
                        ev = json.loads(line)
                        # OpenCode prompt streaming returns events: check for text
                        if isinstance(ev, dict):
                            # common fields: type, delta, text, content
                            if "text" in ev and ev.get("type","").startswith("text"):
                                delta = ev["text"]
                                print(delta, end="", flush=True)
                                full+=delta
                            elif "delta" in ev:
                                print(ev["delta"], end="", flush=True)
                                full+=ev["delta"]
                            elif ev.get("type")=="text.delta":
                                d=ev.get("delta","")
                                print(d, end="", flush=True)
                                full+=d
                            else:
                                # Log other events
                                if ev.get("type") not in ["session.status","step.start"]:
                                    print(f"\n[EV] {ev}", file=sys.stderr)
                                    if "text" in ev:
                                        full+=ev["text"]
                        else:
                            print(line)
                            full+=line
                    except:
                        # Raw text
                        print(line, end="")
                        full+=line
                proc.wait(timeout=300)
                print("\n[done]")
                if full.strip():
                    speak(full.strip()[:800])  # speak first 800 chars to avoid long TTS
                else:
                    # Fallback: get last message from session
                    msgs = run_opencode_api("get", f"/api/session/{session_id}/message")
                    if msgs:
                        print(f"[messages] {json.dumps(msgs)[:2000]}", file=sys.stderr)
            except Exception as e:
                print(f"[prompt error] {e}", file=sys.stderr)
                proc.kill()
        except KeyboardInterrupt:
            speak("Jarvis paused.")
            break
