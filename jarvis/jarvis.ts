import { OpenCode } from "@opencode/sdk"

// Local Jarvis - voice loop with approval
// STT: replace with faster-whisper, TTS: piper, Wake: openWakeWord
// This demo uses text input to simulate voice - swap transcribe()/speak()

async function speak(text: string) {
  console.log(`[JARVIS]: ${text}`)
  // TODO: pipe to piper-tts: `echo "${text}" | piper --model en_US-lessac-medium --output_file - | aplay`
}

async function transcribe(prompt?: string): Promise<string> {
  // TODO: replace with faster-whisper
  // For now, read from stdin to simulate voice
  process.stdout.write(prompt || "[YOU - type voice]: ")
  return new Promise(res => {
    process.stdin.once("data", d => res(d.toString().trim()))
  })
}

await using opencode = await OpenCode.create()
console.log("OpenCode host created. Models:", await opencode.models.list().catch(()=> "check LM Studio server at :1234"))

let session = await opencode.sessions.create({
  location: { directory: "D:\\opencode" },
})
console.log(`Session ${session.id} ready. Using lmstudio/bonsai-27b for tasks, gemma-3-1b for chat.`)

// Handle permission ask -> voice approval
;(async () => {
  for await (const event of await opencode.events.subscribe()) {
    // Permission request events have type containing "permission"
    const e = event as any
    if (e.type?.includes("permission") && e.type?.includes("asked")) {
      const action = e.properties?.action ?? e.action ?? "action"
      const resource = e.properties?.resource ?? e.resource ?? ""
      await speak(`Should I run ${action} ${resource}? Say yes, always, or no.`)
      const ans = (await transcribe()).toLowerCase()
      let reply: "once" | "always" | "reject" = "reject"
      if (ans.includes("always")) reply = "always"
      else if (ans.includes("yes") || ans.includes("approve") || ans.includes("ok")) reply = "once"
      // reply to permission
      try {
        // SDK permission reply - check API: opencode.permission.reply or opencode.permissions.reply
        const api: any = (opencode as any).permissions ?? (opencode as any).permission
        if (api?.reply) await api.reply({ requestID: e.id ?? e.requestID, reply })
        else console.log(`[PERMISSION] Reply ${reply} for ${action} - no API, set permissions to allow in opencode.jsonc for now`)
      } catch (err) { console.error("permission reply failed", err) }
      await speak(reply === "reject" ? "Denied." : "Approved.")
    }
    if (e.type === "session.idle") {
      // optional: speak idle
    }
  }
})()

await speak("Jarvis online. Local models: Gemma 3 1B for quick chat, Bonsai 27B for tasks. Say 'hey jarvis' then your request. Type 'exit' to quit.")

while (true) {
  const text = await transcribe()
  if (!text) continue
  if (text.toLowerCase() === "exit") break
  // Remove wake word if present
  const prompt = text.replace(/hey jarvis,?/i, "").trim() || text

  // Stream response from Bonsai/Gemma
  try {
    const stream = await opencode.sessions.prompt({ sessionID: session.id, text: prompt })
    let full = ""
    for await (const ev of stream as any) {
      if (ev.type === "text" || ev.type === "text.delta") {
        const delta = ev.text ?? ev.delta ?? ""
        full += delta
        // stream to TTS chunk by chunk - here just log
        process.stdout.write(delta)
      }
      if (ev.type === "tool.execute") {
        console.log(`\n[TOOL] ${ev.tool} ${JSON.stringify(ev.input)?.slice(0,200)}`)
      }
    }
    console.log("\n")
    // Final TTS
    // await speak(full)
  } catch (err) {
    console.error("prompt failed - is LM Studio server running on :1234 with model loaded?", err)
    await speak("My local brain is offline. Start LM Studio server on port 1234.")
  }
}
