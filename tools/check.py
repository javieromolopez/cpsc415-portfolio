"""The claim check: plain code that lists claims in an answer the tool results do not support.
Spec behavior 22. It catches shas, dates, and commit claims with nothing behind them; it cannot
catch a wrong *description* of a real commit (see CHECKS.md, What the check cannot catch)."""
import re

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"], start=1)}
MONTH_RE = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DATE_WORDS = re.compile(rf"\b{MONTH_RE}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", re.IGNORECASE)
ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
HEX = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
CLAIM = re.compile(r"\b(committed|pushed)\b|\bcommit\w*\b.*\b(yesterday|today|this week|last week)\b|"
                   r"\b(yesterday|today|this week|last week)\b.*\bcommit", re.IGNORECASE)


def _month(word: str) -> int:
    w = word.lower()
    return next(n for name, n in MONTHS.items() if name.startswith(w[:3]))


def check_answer(answer: str, steps: list) -> dict:
    commits = [c for s in steps if "tool" in s for c in (s.get("result") or {}).get("commits", [])]
    shas = [c["sha"].lower() for c in commits]
    dates = {c["date"] for c in commits}                        # "2026-11-09"
    month_days = {(int(d[5:7]), int(d[8:10])) for d in dates}
    unsupported = []

    for token in HEX.findall(answer):
        if not any(ch.isdigit() for ch in token):               # "defaced", "accede": English, not a sha
            continue
        t = token.lower()
        if not any(s.startswith(t) or t.startswith(s) for s in shas):
            unsupported.append(f"sha {token!r} was not returned by any tool call")
    for m in ISO.finditer(answer):
        if m.group(0) not in dates:
            unsupported.append(f"date {m.group(0)!r} is not the date of any returned commit")
    for m in DATE_WORDS.finditer(answer):
        if (_month(m.group(1)), int(m.group(2))) not in month_days:
            unsupported.append(f"date {m.group(0)!r} is not the date of any returned commit")
    if not commits and CLAIM.search(answer):
        unsupported.append("claims something was committed, but no tool call returned any commits")
    return {"supported": not unsupported, "unsupported": unsupported}
