# Project conventions

<!-- The agent reads this at the start of every session. Keep it short and current.
     Graded: does it reflect how the team actually works? -->

## What this repository is
An AI-enabled personal profile site featuring a chatbot that answers whether visitors should work together with me, grounded strictly in a structured JSON profile.

## Commands
```text
# build
javac -cp ".;lib/*" *.java
# test
java -cp ".;lib/*" Eval
# run
java -cp ".;lib/*" Main
# lint
N/A

# voice/ (Python, Week 7)
pip install -r requirements.txt pytest ruff
python -m pytest voice/tests -v      # no-key tests run free; billed tests skip without a key
ruff check voice
```

## Conventions
- Language and style rules: Java (JDK 17+). Use Jackson for JSON parsing. No other external dependencies unless explicitly approved.
- Where tests live and how the are named: Tests live at the repository root and are named *Eval.java or *Test.java 
- Branch and PR naming. Branches use feature/<short-name> (e.g., feature/profile-schema). PRs use imperative verbs (e.g., 'Add adversarial test set').

## Working rules

For an introductory lab, follow its explicitly assigned stages; the full chain below applies to major projects. Week 1 uses its own minimal repository.

- Write or update `intent/` and `spec.md` before code. Get `plan.md` approved before implementing.
- One feature per branch and pull request. Never push to `main` directly, except where a lab says to commit to main (Week 7).
- Never commit `.env` or `.claude/settings.local.json`.
- Week 7: the spoken interface lives in voice/. Stages assigned: intent, spec,
  plan, tests. Commit to main. The Java chatbot does not exist yet, so voice/
  is Python and uses the course example's profile and answer step until the
  Java chatbot replaces it (before November 30).
- Transcription and speech calls are billed. One transcription per clip, one
  speech call per answer, never a model call inside a loop of tests. Fixture
  clips are WAV; expected.json is written by a person before the model hears it.
- The spoken answer is the chatbot's answer: the refuse-to-fabricate rule
  applies to what is said aloud exactly as to what is typed.

## Common mistakes
- Do not write code before approval.
- The chatbot must never hallucinate expertise; distinguish shipped work from aspirational learning strictly.
- Handle API and JSON errors gracefully (fail fast on malformed JSON and clearly surface 403 Key Limit errors).
- Format Markdown tables perfectly using valid separator rows (`|---|---|`) to prevent GitHub rendering failures.
