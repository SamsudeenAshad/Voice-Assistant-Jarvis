# Voice-Assistant-Jarvis

Local, offline Jarvis-like voice assistant for Ashad — built on **OpenCode** + **LM Studio** (Gemma 3 1B + Bonsai 27B) + local STT/TTS.

> 🎙️ **Wake:** `hey javis` / `hey javis i am ashad here` — **only Ashad's voice** unlocks it  
> 🧠 **Brain:** 100% local via LM Studio (`127.0.0.1:1234`) — Gemma 3 1B for fast chat, Bonsai 27B for tasks  
> ✅ **Approval:** Every `shell`/`edit` asks Ashad for voice `yes / always / no` before executing  
> 💻 **Laptop control:** Volume, brightness, open apps, file ops — all via approved shell

## Architecture

```
Mic -> Wake (faster-whisper) + Speaker Verify (resemblyzer) -> STT -> OpenCode SDK -> Bonsai/Gemma -> TTS (piper / SAPI)
                                  |-> Permission ask -> "Should I run ...?" -> STT yes/no -> execute
```

## Quick Start

1. **LM Studio** — `Local Server` → Load `google/gemma-3-1b` (720 MB) + `prism-ml/bonsai-27b` (4.7 GB Q1_0) → `Start Server` on `127.0.0.1:1234` with CORS.
2. **Install voice** (optional, fallback to Windows SAPI):
   ```powershell
   pip install -r jarvis/requirements.txt
   ```
3. **Enroll Ashad's voice** (locks wake to you):
   ```powershell
   python jarvis/enroll.py   # 3× say "hey javis i am ashad here"
   ```
4. **Run:**
   ```powershell
   python jarvis/jarvis_voice.py
   # Wake: "hey javis" -> "Yes Ashad?" -> "create file hello.txt" -> asks approval
   ```

Test without mic: `python jarvis/jarvis_voice.py` falls back to keyboard.

## Project Structure

- `opencode.jsonc` — OpenCode config (LM Studio provider, permissions, agents)
- `jarvis/jarvis_voice.py` — Main loop (wake → STT → OpenCode → TTS + permission watcher)
- `jarvis/jarvis.ts` — TypeScript SDK alternative (uses `@opencode/sdk`)
- `jarvis/enroll.py` — Enroll Ashad's voice to `ashad_voice.npy` (ignored by git)
- `jarvis/wake_verified.py` — Verified wake test
- `jarvis/stt.py` — faster-whisper STT
- `jarvis/tts.py` — piper-tts + SAPI fallback
- `jarvis/wake.py` — Simple wake

See `jarvis/README.md` for details.

## Laptop Control

Allowed via `permissions:ask` in `opencode.jsonc:15`:
- `shell` examples: `(New-Object -comObject WScript.Shell).SendKeys([char]175)` (volume), `start chrome`, `Set-ItemProperty` (brightness), file `edit`/`write`.
- Jarvis always asks before running. Say `yes`, `always`, or `no`.

## Models

Located at `C:\Users\HP\.lmstudio\models`:
- `lmstudio-community/gemma-3-1B-it-QAT-GGUF/gemma-3-1B-it-QAT-Q4_0.gguf`
- `lmstudio-community/Bonsai-27B-GGUF/Bonsai-27B-Q1_0.gguf`

LM Studio serves them as `gemma-3-1b` & `prism-ml/bonsai-27b` / `bonsai-27b`.
