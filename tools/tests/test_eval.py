"""The billed eval: five questions on the class model and the comparison, through the chatbot's own
system prompt and the real tool. Skipped without a key. About one or two cents for both models.

    python -m pytest tools/tests/test_eval.py -v -s

Every run appends one line per question per model to tools/eval-results.jsonl (tools called with
their arguments, chat steps, pass or fail with the reasons, cost, seconds, the answer), which is
where the table in tools/CHECKS.md comes from. Spec behaviors 22 and 26.
"""
import json
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "voice"))

KEY = os.environ.get("OPENROUTER_API_KEY")
pytestmark = pytest.mark.skipif(not KEY, reason="OPENROUTER_API_KEY not set: the billed eval is skipped")
MODELS = os.environ.get("EVAL_MODELS", "minimax/minimax-m3,xiaomi/mimo-v2.6-flash").split(",")
RESULTS = ROOT / "tools" / "eval-results.jsonl"

CASES = [
    # id, question, repos that must be asked for, words the answer must contain, words it must not
    ("latest", "What has Javier been committing to TP1 lately?", {"javieromolopez/TP1"}, [], []),
    ("missing", "What are the latest commits in Javier's Kubernetes repository?", set(), [],
     ["committed", "pushed"]),
    ("profile", "Does Javier know Java?", set(), ["java"], []),
    ("yesterday", "What did Javier commit yesterday?", set(), [], ["yesterday he", "yesterday, he"]),
    ("two_repos", "What changed most recently in his receipt reader and in his RAG project?",
     {"javieromolopez/cpsc415-week05", "javieromolopez/cpsc415-week04"}, [], []),
]


def asked_repos(steps):
    repos = set()
    for s in steps:
        if s.get("tool") == "recent_commits":
            try:
                repos.add(json.loads(s["arguments"]).get("repo"))
            except (json.JSONDecodeError, AttributeError):
                pass
    return repos


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_case(model, case):
    from server import SYSTEM, client  # the chatbot's own prompt and client

    from tools.loop import run

    cid, question, must_ask, must_say, must_not_say = case
    r = run(question, SYSTEM, model=model, client=client)
    low = r["answer"].lower()
    failures = []
    if r["stopped_by"] != "answer":
        failures.append(f"stopped by {r['stopped_by']}")
    if not must_ask <= asked_repos(r["steps"]):
        failures.append(f"expected calls for {sorted(must_ask - asked_repos(r['steps']))}")
    failures += [f"answer should mention {w!r}" for w in must_say if w not in low]
    failures += [f"answer must not say {w!r}" for w in must_not_say if w in low]
    if not r["check"]["supported"]:
        failures += r["check"]["unsupported"]
    model_text = next((s["answer"] for s in reversed(r["steps"]) if "answer" in s), r["answer"])
    line = {"when": time.strftime("%Y-%m-%d %H:%M"), "model": model, "case": cid, "question": question,
            "calls": [f"{s['tool']}({s['arguments']})" for s in r["steps"] if "tool" in s],
            "steps": max((s["step"] for s in r["steps"]), default=0), "stopped_by": r["stopped_by"],
            "passed": not failures, "failures": failures, "cost": r["cost"], "seconds": r["seconds"],
            "answer": r["answer"], "model_text": model_text,
            "results": [s["result"] for s in r["steps"] if "tool" in s]}
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    print(f"\n[{model}] {cid}: calls={line['calls']} steps={line['steps']} cost=${r['cost']:.6f} "
          f"{r['seconds']}s  {'PASS' if not failures else 'FAIL ' + str(failures)}\n  {r['answer']}")
    assert not failures, failures
