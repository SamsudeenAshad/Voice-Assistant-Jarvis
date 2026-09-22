# Jarvis - Local Voice Assistant + OpenCode + LM Studio

Models: `Gemma 3 1B IT QAT Q4_0` (fast chat) + `Bonsai 27B Q1_0` (tasks) at `C:\Users\HP\.lmstudio\models`

## Quick Start

1. **Start LM Studio Server**
   - Open LM Studio -> Left bar `Local Server`
   - Load `Bonsai-27B-Q1_0.gguf` (set context 32768)
   - Optionally also load `gemma-3-1B-it-QAT-Q4_0.gguf` (for faster chat - you can switch via `/models`)
   - `Start Server` on `http://127.0.0.1:1234`
   - Verify: `curl.exe -s http://127.0.0.1:1234/v1/models`

2. **Install voice deps (optional, for real voice)**
   ```powershell
   pip install -r D:\opencode\jarvis\requirements.txt
   # If piper-tts fails, fallback uses Windows SAPI automatically
   ```

3. **Text mode (no mic needed) - test now**
   ```powershell
   cd D:\opencode\jarvis
   python jarvis_voice.py
   # Speak/type: "hey jarvis write a poem about AI" -> Bonsai responds
   # Speak/type: "create file hello.txt with hello world" -> asks approval -> say "yes"
   ```

4. **Voice mode (mic + speaker)**
   ```powershell
   python stt.py --duration 7   # test mic
   python tts.py "Hello sir, Jarvis is online"
   python wake.py              # test wake word
   python jarvis_voice.py      # full loop
   ```

5. **Approval flow**
   - Config `D:\opencode\opencode.jsonc` has `permissions: ask` for `shell`/`edit`.
   - Jarvis polls `GET /api/session/{id}/permission`, TTS asks "Should I run ...?", STT listens for "yes/always/no", then `POST /permission/{id}/reply`.

## Switch Models
- Text: `opencode --model lmstudio/gemma-3-1b` for quick chat
- Or edit `D:\opencode\opencode.jsonc` -> `model: lmstudio/bonsai-27b` -> `agents.build.model`

## Troubleshooting
- `LMStudio Not running` -> start server as above
- `voice not found` -> first run downloads wax, fallback SAPI will speak anyway
- `opencode api failed` -> `opencode service restart` then retry
