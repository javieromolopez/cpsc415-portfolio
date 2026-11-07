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

## Transcription, per clip per model

_(to fill: word error rate, missing words, audio seconds, cost, seconds per call)_

## Which model got my name right

_(to fill after listening)_

## The answer, spoken

_(to fill: characters, bytes, estimated cost, seconds; what each voice did with my name, "CPSC 415", "RAG")_

## Browser check

_(to fill)_

## One turn

_(to fill: transcript, answer, three costs, total)_
