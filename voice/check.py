"""Check a transcript in plain code. No model, no key (spec.md behaviors 8-10).

A transcript is model output. The program cannot hear the audio, but it can measure:
how far the words drift from what a person wrote down first (word error rate),
whether the words that had to survive did (my name, the course number), and
whether anything came back at all. Adapted from the course voice-loop example.
"""
import re

_WORD = re.compile(r"[a-z0-9']+")
DEFAULT_MAX_WER = 0.15


def words(text: str | None) -> list[str]:
    """Lower-case words without punctuation, so 'Hello, world!' == 'hello world'."""
    return _WORD.findall((text or "").lower().replace("’", "'"))


def wer(expected: str, got: str | None) -> float:
    """Word error rate: insertions, deletions and substitutions per expected word.
    0.0 is perfect; an empty transcript scores 1.0."""
    e, g = words(expected), words(got)
    if not e:
        return 0.0 if not g else 1.0
    if not g:
        return 1.0
    prev = list(range(len(g) + 1))                      # Levenshtein over words, one row at a time
    for i, ew in enumerate(e, 1):
        cur = [i]
        for j, gw in enumerate(g, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ew != gw)))
        prev = cur
    return prev[-1] / len(e)


def compare(expected: str, got: str | None, must_contain: list[str] | None = None,
            max_wer: float = DEFAULT_MAX_WER) -> dict:
    """The verdict recorded per clip. ok only when the rate is within tolerance, every required
    word survived, and something came back. Never raises on an empty or missing transcript."""
    heard = "".join(words(got))                         # spacing-insensitive: "CPSC415" still has "CPSC 415"
    missing = [w for w in (must_contain or []) if "".join(words(w)) not in heard]
    empty = not words(got)
    rate = wer(expected, got)
    return {"ok": rate <= max_wer and not missing and not empty,
            "wer": round(rate, 3), "missing": missing, "empty": empty}
