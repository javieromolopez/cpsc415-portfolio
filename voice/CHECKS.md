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

## The answer, spoken

_(to fill: characters, bytes, estimated cost, seconds; what each voice did with my name, "CPSC 415", "RAG")_

## Browser check

_(to fill)_

## One turn

_(to fill: transcript, answer, three costs, total)_
