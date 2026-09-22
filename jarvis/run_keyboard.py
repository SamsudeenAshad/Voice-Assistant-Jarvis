#!/usr/bin/env python
"""Lightweight Jarvis runner - keyboard wake (no faster-whisper needed), uses LM Studio directly for demo"""
import os, sys, json, subprocess, urllib.request, re, time

LM_URL = "http://127.0.0.1:1234/v1/chat/completions"
OP_DIR = r"D:\opencode"

def chat(model, prompt, max_tokens=120):
    data = json.dumps({
        "model": model,
        "messages": [{"role":"user","content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode('utf-8')
    req = urllib.request.Request(LM_URL, data=data, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read().decode('utf-8'))
        return j["choices"][0]["message"]["content"]

def speak(text):
    print(f"\n[JARVIS]: {text}\n")
    try:
        ps = f'Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate=1; $s.Speak("{text.replace(chr(34), chr(39))[:400]}");'
        subprocess.run(["powershell","-Command", ps], timeout=12)
    except: pass

def laptop_control(cmd):
    """Demo laptop control via shell - asks approval"""
    print(f"[LAPTOP CONTROL REQUEST] {cmd}")
    speak(f"Should I run {cmd}? Say yes or no.")
    ans = input("[Ashad approval - type yes/no/always]: ").strip().lower()
    if "yes" in ans or "always" in ans:
        try:
            # Example controls
            if "volume" in cmd.lower():
                # Volume up via WScript.Shell
                ps = "(New-Object -comObject WScript.Shell).SendKeys([char]175)"
                subprocess.run(["powershell","-Command", ps], timeout=5)
                return "Volume increased."
            elif "notepad" in cmd.lower() or "open" in cmd.lower():
                subprocess.Popen(["notepad.exe"])
                return "Opened Notepad."
            elif "chrome" in cmd.lower():
                subprocess.Popen(["cmd","/c","start","chrome"])
                return "Opened Chrome."
            elif "brightness" in cmd.lower():
                return "Brightness control requires approval - simulated."
            else:
                # Generic shell via opencode permission demo
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, cwd=OP_DIR)
                return result.stdout[:500] or result.stderr[:500] or "Done."
        except Exception as e:
            return f"Failed: {e}"
    else:
        return "Denied by Ashad."

print("=== JARVIS Keyboard Demo (Ashad-only: hey javis) ===")
print("LM Studio: gemma-3-1b (fast) + bonsai-27b (smart) at 127.0.0.1:1234")
print("Models idle: " + subprocess.run(["lms","ps"], capture_output=True, text=True).stdout.strip().replace("\n"," | "))
print("\nWake phrases: 'hey javis' or 'hey javis i am ashad here' (typed) - only Ashad")
print("Type 'exit' to quit. Laptop control demo after wake.\n")

# Enrollment check
if not os.path.exists(os.path.join(os.path.dirname(__file__), "ashad_voice.npy")):
    print("[VOICE] No ashad_voice.npy yet - voice lock disabled for keyboard demo (run enroll.py for real mic lock).")

while True:
    wake = input("[Type wake - hey javis / hey javis i am ashad here]: ").strip()
    if not wake: continue
    if wake.lower() in ["exit","quit"]: break
    wake_low = wake.lower()
    is_wake = any(x in wake_low for x in ["hey javis","hey jarvis","javis i am ashad","jarvis i am ashad"])
    if not is_wake:
        print("[IGNORED] Say 'hey javis' to wake. (Other voices ignored in real mic mode)")
        continue
    # Check for "i am ashad here" - personalized
    if "ashad" in wake_low:
        speak("Hello Ashad, I am Jarvis. How can I help?")
        print("[WAKE] hey javis i am ashad here -> VERIFIED ASHAD")
    else:
        speak("Yes Ashad?")
        print("[WAKE] hey javis -> VERIFIED (keyboard demo)")

    cmd = input("[Ashad command - e.g. 'what is 2+2' or 'open notepad' or 'volume up']: ").strip()
    if not cmd: continue
    if cmd.lower() in ["exit","quit"]: break

    # Laptop control intents
    if any(k in cmd.lower() for k in ["open","volume","brightness","chrome","notepad","calculator","control"]):
        result = laptop_control(cmd)
        print(f"[RESULT] {result}")
        speak(result)
        continue

    # Local conversation via Gemma (fast) - use Bonsai for complex tasks if needed
    model = "gemma-3-1b"
    if any(k in cmd.lower() for k in ["create file","write code","build","task","project","explain code"]):
        model = "bonsai-27b"
        print(f"[BRAIN] Using Bonsai 27B for task...")
        speak("Working on your task with Bonsai, Ashad.")
    else:
        print(f"[BRAIN] Using Gemma 3 1B for chat...")

    try:
        # Add Jarvis personality
        prompt = f"You are Jarvis, a helpful local voice assistant for Ashad. Be concise, friendly, refer to Ashad by name. User says: {cmd}"
        resp = chat(model, prompt, max_tokens=150)
        print(f"[JARVIS via {model}]: {resp}")
        speak(resp)
        # Demo approval for file edits
        if "create file" in cmd.lower() or "write" in cmd.lower():
            fname = "hello_jarvis.txt"
            print(f"[PERMISSION ASK] Should I create {fname}? (voice approval simulation)")
            speak(f"Should I create file {fname}?")
            ans = input("[Ashad - yes/no]: ").strip().lower()
            if "yes" in ans:
                open(os.path.join(OP_DIR, fname),"w").write(resp[:1000])
                print(f"[DONE] Created D:\\opencode\\{fname}")
                speak("File created, Ashad.")
            else:
                print("[DENIED]")
    except Exception as e:
        print(f"[ERROR] {e}")
        speak("My local brain is thinking slowly, try again.")
