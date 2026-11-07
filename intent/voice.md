# Intent: voice

## Goal
A visitor to the portfolio site can ask the chatbot a question out loud and hear the answer. The server transcribes the recording, the chatbot answers from the profile exactly as it does for typed questions, and the answer is spoken back. The transcript is model output and may be wrong, so the program checks it in code where it can and shows it to the visitor where it cannot.

## Who it is for
- **Recruiters and engineering managers** who would rather ask than type, for example on a phone. Today they must type into the chat box.
- **Me, as the developer**, who needs to know when the transcriber got a name or number wrong before a recruiter does. Today nothing would tell me.

## Constraints
- **Language:** Python for `voice/`, with the `openrouter` SDK. The Java chatbot is not built yet; the course's voice-loop example is Python, and the two requests are small. The Java chatbot takes over the answer step before November 30.
- **Profile, for now:** the course example's `profile.json` (a fictional student, Sam Rivera) and its answer step, stated in `voice/CHECKS.md`. My own profile replaces it when the Java chatbot exists.
- **Models:** transcription `openai/whisper-large-v3-turbo` compared against `elevenlabs/scribe-v2`; speech `microsoft/mai-voice-2.1-flash` with a named voice, compared against a second voice or model; chat answer `minimax/minimax-m3` (the example's model).
- **Cost:** the whole lab under $0.05. One transcription per clip, one speech call per answer, never a model call inside a loop of tests.
- **Key:** stays on the server. The browser sends only audio and never sees the key or the provider.
- **Deadline:** Monday, November 9, 2026, 1:30 PM, tag `week07-submitted`.

## Not in scope
- Real-time speech-to-speech, streaming audio, or conversation memory.
- Languages other than English (no language experiment this week).
- Deploying the site (that is the November 30 milestone).
- Building the Java chatbot or writing my own `profile.json`.
- Voice cloning or a custom voice.

## Success looks like
1. **The transcript is checked by code.** For each of my two clips, `CHECKS.md` shows the word error rate against what I wrote down before recording, within a tolerance of **0.15**, and whether **"Javier Romo"** and **"415"** came through on both transcription models. An empty transcript is reported as a failure, not a crash.
2. **The chatbot still refuses to fabricate out loud.** Asking by voice *"Have you shipped anything written in Rust?"* gets a spoken answer that says Rust is on the "not yet" list. Asking *"How much did a query cost in your RAG project?"* gets the figure from the profile, nothing invented.
3. **One full turn works with the key on the server.** I hold the button, ask a question, read the transcript, read and hear an answer of at most three sentences, and the browser check shows that no request carried the key or went to the provider. The three costs and the total for that turn are in `CHECKS.md`.

## My clips (text fixed before any model hears them)
1. "Hi, I'm Javier Romo from CPSC 415. How much did a query cost in your RAG project?" (The profile can answer this one.)
2. "This is Javier Romo again. Have you shipped anything written in Rust?" (The profile cannot: Rust is "not yet".)

## Open questions
- If the transcriber turns my name into a different word, the chatbot still answers the question (the name is not needed to answer). The checker flags it; nothing at runtime does. Is that acceptable for a portfolio site? (Proposed: yes, and the visitor sees the transcript.)

**Approved by:** Javier Romo, November 6, 2026
