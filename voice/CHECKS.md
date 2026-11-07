# Week 7 checks: the spoken interface

**Profile used this week:** the course voice-loop example's `profile.json` (a fictional student, Sam Rivera) and its answer step. My Java chatbot does not exist yet; it replaces both before November 30.

## No-key tests

`python -m pytest voice/tests/test_check.py -v`: 14 passed in 0.12 s (November 6, 2026).

- The tests were committed failing first (`ModuleNotFoundError: No module named 'check'`), then `check.py` was written.
- The first green run still had 4 failures. They were a bug in the test, not the checker: my 13-word sample sentence had only 12 words, and `test_said_has_thirteen_words` caught it. I fixed the sentence, not the checker.

## Linter

`ruff check voice`:
- First run: 1 finding, `RUF100` (an unused `# noqa: E402` on the test's import). Removed.
- Second run: all checks passed.
- After adding `transcribe.py`, `speak.py`, and `tests/test_eval.py`: 1 finding, `I001` (import order in `transcribe.py`: ruff treats the local `check` module as third-party). Fixed with `ruff check --fix`; all checks passed.
- Running ruff from inside `voice/` then flagged the same `I001` the other way round: from there, `check` looks first-party. Added `voice/ruff.toml` declaring `check`, `transcribe`, `speak`, and `server` as first-party. `ruff check voice` from the root and `ruff check .` from `voice/` now both pass.

## Transcription, per clip per model

November 6, 2026. One call per clip per model: `python transcribe.py --set clips/expected.json --out transcripts-whisper.json`, then the same with `--model elevenlabs/scribe-v2 --out transcripts-scribe.json`. `expected.json` was committed (`6f266ba`) before either call. Tolerance is 0.15, except 0.2 on `clip-02` (the course's note).

`me-01` and `me-02` are my own voice, recorded on a laptop microphone with Windows Sound Recorder (M4A). The `clip-0x` files are the course's model-voiced WAV fixtures.

| Clip | Model | Verdict | WER | Missing | Audio s | Cost | Call s | What it heard (the difference) |
|---|---|---|---|---|---|---|---|---|
| me-01 | whisper-large-v3-turbo | **FAIL** | 0.059 | RAG | 9.36 | $0.000031 | 3.4 | "your **Rack** project" |
| me-01 | scribe-v2 | ok | 0.000 | none | 9.37 | $0.000572 | 2.0 | exact |
| me-02 | whisper-large-v3-turbo | **FAIL** | 0.167 | none | 7.10 | $0.000024 | 2.6 | "Javier Romo **`Iqu�n`**" for "again" (the reply itself contained U+FFFD, the Unicode replacement character) |
| me-02 | scribe-v2 | **FAIL** | 0.083 | Javier Romo | 7.10 | $0.000434 | 1.5 | "Javier **Romu** again" |
| clip-01 | whisper-large-v3-turbo | ok | 0.000 | none | 6.38 | $0.000021 | 1.3 | exact |
| clip-01 | scribe-v2 | ok | 0.000 | none | 6.38 | $0.000390 | 1.4 | exact |
| clip-02 | whisper-large-v3-turbo | ok | 0.188 | none | 8.06 | $0.000027 | 1.6 | "boot camp", and "Music" appended to the silence |
| clip-02 | scribe-v2 | ok | 0.125 | none | 8.06 | $0.000493 | 1.4 | "boot camp" (the example's README says Scribe read it as one word; here it did not) |
| clip-03 | whisper-large-v3-turbo | ok | 0.000 | none | 7.71 | $0.000026 | 3.8 | exact |
| clip-03 | scribe-v2 | ok | 0.000 | none | 7.71 | $0.000471 | 2.1 | exact |

**Totals:** Whisper $0.00013 for five clips; Scribe $0.00236 (about 18 times as much).

**What the numbers say:**
- Both course fixtures that a model spoke passed on both transcribers. Three of the four results on my own voice failed. A person in a room is the harder test, as the lab predicted.
- The failures are in exactly the places that matter: a project name ("RAG" → "Rack"), my surname ("Romo" → "Romu"), and an invented word. The question text around them was right.
- `must_contain` caught what the rate alone would have passed. Scribe's "Romu" is 1 word in 12 (0.083, inside 0.15), and Whisper's "Rack" is 1 in 17 (0.059). Both still fail because of the required words.
- Whisper's me-02 is the reverse case: no required word is missing, but "again" became a garbled word and the rate went over tolerance.
- Neither transcriber was right on both of my clips. Whisper kept my name both times but lost "RAG". Scribe got "RAG" but lost "Romo" once.
- I did not edit `expected.json` to match any transcript.

## Which model got my name right

**Whisper.** I played both of my clips and read the two transcripts myself. Whisper wrote "Javier Romo" correctly on both clips. Scribe got it right on `me-01` but wrote "Romu" on `me-02`.

Whisper is still not the safe choice, though. On the same clips it turned "RAG" into "Rack" and garbled "again". The second transcriber is what showed each one's errors: without Scribe I would have trusted "Rack", and without Whisper I would have trusted "Romu".

**What I heard in my own clips:** I said "Javier" correctly, and I pronounce "RAG" as a word ("rag"), not as letters. That explains Whisper's "Rack": a real English word one sound away from what I said. Scribe wrote "RAG" because it recognized the term from the rest of the sentence. The checker cannot tell which of these happened; only listening can. If the deployed chatbot gets voice questions about RAG, the answer step should treat "rack project" as a likely mishearing, or the page should show the transcript so the visitor can see it was misheard.

## Billed eval

`python -m pytest voice/tests/test_eval.py -v -s` (Whisper, one call per clip, plus one speech call), November 6, 2026. It ran twice:
- **Run 1 (by accident):** `pytest voice/tests` with the key set also runs the billed eval: 19 passed, 2 failed. I had cut the output to its last lines, so the details were lost.
- **Run 2 (kept):** 6 passed, 1 failed, in 64.7 s. Cost about $0.0011: five transcriptions about $0.00022, one speech call $0.00087.

| Test | Result | Detail |
|---|---|---|
| expected.json exists | passed | |
| me-01.m4a | **failed** | wer 0.059, missing `RAG`: "your Rack project" again, the same as the first Whisper run |
| me-02.m4a | passed | wer 0.0, "This is Javier Romo again". Exact this time, at $0.000111 instead of $0.000024. The garbled `Iqu�n` from the first run did not repeat; the different price suggests a different host served the call |
| clip-01.wav | passed | wer 0.0 |
| clip-02.wav | passed | wer 0.188, "boot camp" plus "Music" (within the 0.2 the course set) |
| clip-03.wav | passed | wer 0.0 |
| speech comes back as audio | passed | 83,040 bytes of MP3, $0.00087 |

The eval's failure on `me-01` is the correct outcome: Whisper consistently hears "RAG" as "Rack" in my voice. I did not change the expected text or the tolerance to make it pass. The same clip transcribed twice gave two different results on `me-02`, so one transcription per clip is a sample, not a verdict.

## The answer, spoken

The chatbot's typed answer to `me-01` (one chat call on `minimax/minimax-m3`, $0.00044), saved as `answer-me-01.txt`:

> Hey Javier! In the RAG project over the course notes, a query cost under a tenth of a cent — the index had 165 chunks and that was the per-query spend on embeddings. The takeaway Sam noted was that retrieval, not the model, was what decided answer quality.

**Grounding:**
- "Under a tenth of a cent", "165 chunks", and "retrieval, not the model" are all in the profile.
- "The per-query spend on embeddings" is not. The profile gives the cost of a query, not which part of it was embeddings. This is a small embellishment, and the refuse-to-fabricate rule says it should not be there.
- The answer is three sentences, with no markdown.

Spoken twice, one call each, from the same 256-character text:

| Voice | File | Chars | Bytes | Cost (estimated) | Seconds |
|---|---|---|---|---|---|
| `microsoft/mai-voice-2.1-flash` / `en-US-Harper` (class default) | `answer-harper.mp3` | 256 | 372,480 | $0.00384 | 22.1 |
| `microsoft/mai-voice-2.1-flash` / `en-IN-Priya` (comparison) | `answer-priya.mp3` | 256 | 443,520 | $0.00384 | 15.9 |

Both costs are estimated from the catalog price per character: the generation record did not exist yet when `speak.py` looked it up.

**What went wrong first:**
- Priya timed out at the SDK's default timeout twice on the full answer, and once on the 20-character sentence "Hello from CPSC 415." (`httpx.ReadTimeout`, about 16 s). The provider was slow to start sending audio; it was not a problem with the length of the text.
- The class model took 22 s for Harper, where the course measured under 1.4 s on October 26.
- Fix: `speak.py` and `server.py` now create the client with `timeout_ms` from `SPEECH_TIMEOUT_MS` (default 120,000). Priya then answered in 15.9 s.
- Whether the three timed-out calls were billed is not known; none of them returned a generation id.

**What each voice did with my name, "RAG", and "165":** I listened to both. Harper and Priya both pronounced "Javier" correctly, said "RAG" as a word ("rag") rather than spelling it out, and read "165" naturally as a number. I heard no difference on these three. The difference between the voices was the accent and the timing: Priya's file is 19% larger for the same text, at the same price per character. (The answer did not contain "CPSC 415", so that could not be checked here.)

## Browser check

_(to fill)_

## One turn

_(to fill: transcript, answer, three costs, total)_
