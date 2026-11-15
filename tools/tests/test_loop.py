"""No-key tests for the tool loop: a scripted fake model and stubbed tool functions.

    python -m pytest tools/tests -v        # no key, no network, well under a second

The fake client returns the replies each test scripted, in order, so a test says exactly what the
model "did" and checks what our program did about it. A real model only misbehaves now and then;
this one misbehaves on demand. Behavior numbers refer to the "Week 8: one tool" section of spec.md.
"""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))      # the repository root

from tools.check import check_answer
from tools.github import TOOL
from tools.loop import (CAP_SENTENCE, CLAIM_SENTENCE, GITHUB_DOWN_SENTENCE, run, run_tool,
                        validate)

SYSTEM = "You answer questions about Javier."
TP1 = {"repo": "javieromolopez/TP1", "commits": [
    {"sha": "a1b2c3d", "date": "2026-11-09", "message": "Critic: read the image, not the prompt"},
    {"sha": "e4f5a6b", "date": "2026-11-02", "message": "Eval: three repeats per topic"}]}


# ---- a scripted model ---------------------------------------------------------------------------
def tool_call(name, arguments, call_id="call_1"):
    """One reply asking for one tool. `arguments` is the JSON *string* the model wrote."""
    return calls((name, arguments, call_id))


def calls(*requests):
    """One reply asking for several tools at once: (name, arguments, id) triples."""
    tcs = [NS(id=i, type="function", function=NS(name=n, arguments=a)) for n, a, i in requests]
    return NS(choices=[NS(message=NS(content="", tool_calls=tcs), finish_reason="tool_calls")],
              usage=NS(cost=0.0001))


def answer(text):
    return NS(choices=[NS(message=NS(content=text, tool_calls=None), finish_reason="stop")],
              usage=NS(cost=0.0001))


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.sent = []                                   # every request the loop made

    @property
    def chat(self):
        return self

    def send(self, **kwargs):
        self.sent.append(copy.deepcopy(kwargs))          # the loop mutates its message list
        if not self.replies:
            raise AssertionError("the loop asked the model again after the script ran out")
        return self.replies.pop(0)


class Stub:
    """Stands in for recent_commits: counts calls, remembers arguments, never touches the network."""
    def __init__(self, result=TP1):
        self.result, self.calls = result, []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def go(replies, stub=None, **kw):
    client, stub = FakeClient(replies), stub or Stub()
    r = run("What has Javier committed to TP1?", SYSTEM, client=client,
            functions={"recent_commits": stub, **kw.pop("functions", {})}, **kw)
    return r, client, stub


# ---- misuse case 1: the single-shot call (behaviors 15, 24) ------------------------------------
def test_single_shot_result_goes_back_as_a_tool_message_with_the_right_id():
    r, client, stub = go([tool_call("recent_commits", '{"repo": "javieromolopez/TP1"}', "call_7"),
                          answer("Lately Javier fixed the critic so it reads the image, on November 9.")])
    assert stub.calls == [{"repo": "javieromolopez/TP1"}]
    assert len(client.sent) == 2 and r["stopped_by"] == "answer"
    last = client.sent[1]["messages"][-1]
    assert last["role"] == "tool" and last["tool_call_id"] == "call_7"
    assert json.loads(last["content"]) == TP1
    assistant = client.sent[1]["messages"][-2]                  # the request, recorded as it was made
    assert assistant["role"] == "assistant" and assistant["tool_calls"][0]["id"] == "call_7"
    assert r["calls"] == ["recent_commits"] and r["check"]["supported"]


def test_the_schema_is_sent_with_every_request():
    _, client, _ = go([tool_call("recent_commits", '{"repo": "javieromolopez/TP1"}'), answer("ok")])
    assert all(req["tools"] == [TOOL] for req in client.sent)
    fn = TOOL["function"]
    assert fn["name"] == "recent_commits" and fn["parameters"]["required"] == ["repo"]
    assert fn["parameters"]["additionalProperties"] is False


# ---- misuse case 2: bad arguments, then the model corrects itself (behavior 16) -----------------
def test_bad_arguments_get_an_error_result_and_the_loop_continues():
    r, client, stub = go([tool_call("recent_commits", '{"repository": "TP1"}', "call_1"),
                          tool_call("recent_commits", '{"repo": "javieromolopez/TP1"}', "call_2"),
                          answer("Javier's latest TP1 commit is about the critic.")])
    err = r["steps"][0]["result"]["error"]
    assert "unexpected argument 'repository'" in err and "missing required argument 'repo'" in err
    second = client.sent[1]["messages"][-1]                     # the error reached the model
    assert second["role"] == "tool" and second["tool_call_id"] == "call_1"
    assert "error" in json.loads(second["content"])
    assert stub.calls == [{"repo": "javieromolopez/TP1"}]       # only the corrected call ran
    assert r["stopped_by"] == "answer" and len(client.sent) == 3


def test_arguments_that_are_not_json_are_an_error_not_a_crash():
    assert "not valid JSON" in run_tool("recent_commits", "{repo: TP1", functions={})["error"]


def test_count_must_be_an_integer_from_1_to_10():
    assert validate("recent_commits", {"repo": "javieromolopez/TP1", "count": 5}) is None
    for bad in ("5", True, 0, 11, 2.5):
        assert "count" in validate("recent_commits", {"repo": "javieromolopez/TP1", "count": bad})


def test_repo_must_be_a_string():
    assert "'repo' must be a string" in validate("recent_commits", {"repo": 7})


def test_a_repository_that_is_not_javiers_is_refused_without_running():
    stub = Stub()
    r = run_tool("recent_commits", '{"repo": "torvalds/linux"}', functions={"recent_commits": stub})
    assert "only javieromolopez/<name>" in r["error"] and stub.calls == []
    assert "only javieromolopez/<name>" in run_tool("recent_commits", '{"repo": "TP1"}',
                                                    functions={"recent_commits": stub})["error"]


# ---- misuse case 3: a tool that does not exist (behavior 19) ------------------------------------
def test_unknown_tool_gets_an_error_result_and_nothing_runs():
    r, client, stub = go([tool_call("delete_repo", '{"repo": "javieromolopez/TP1"}'),
                          answer("I can only look up commits.")])
    err = r["steps"][0]["result"]["error"]
    assert "unknown tool 'delete_repo'" in err and "recent_commits" in err
    assert stub.calls == [] and r["stopped_by"] == "answer" and len(client.sent) == 2


# ---- misuse case 4: the endless caller (behavior 20) --------------------------------------------
def test_endless_caller_is_stopped_by_the_cap_and_the_answer_is_the_programs():
    replies = [tool_call("recent_commits", '{"repo": "javieromolopez/TP1"}', f"call_{i}") for i in range(10)]
    r, client, stub = go(replies)
    assert len(client.sent) == 4                       # four chat calls, never a fifth
    assert r["stopped_by"] == "cap" and r["answer"] == CAP_SENTENCE
    assert len([s for s in r["steps"] if "tool" in s]) == 4


def test_one_reply_with_six_calls_runs_only_four():
    six = calls(*[("recent_commits", '{"repo": "javieromolopez/TP1"}', f"call_{i}") for i in range(6)])
    r, client, stub = go([six, answer("Javier worked on the critic.")])
    assert len(stub.calls) == 4
    results = [s["result"] for s in r["steps"] if "tool" in s]
    assert all("tool call limit reached" in res["error"] for res in results[4:])
    ids = [m["tool_call_id"] for m in client.sent[1]["messages"] if m["role"] == "tool"]
    assert ids == [f"call_{i}" for i in range(6)]          # every request still gets its own result


# ---- misuse case 5: the side effect held (behavior 23) ------------------------------------------
NOTIFY = {"type": "function", "function": {
    "name": "notify_javier", "description": "Test-only tool with a side effect.",
    "parameters": {"type": "object", "properties": {"message": {"type": "string"}},
                   "required": ["message"], "additionalProperties": False}}}


def test_a_side_effect_is_recorded_as_pending_and_does_not_happen():
    notify = Stub(result={"sent": True})
    r, client, _ = go([tool_call("notify_javier", '{"message": "Hire this person"}'),
                       answer("I've passed that on.")],
                      tools=[TOOL, NOTIFY], functions={"notify_javier": notify},
                      side_effects=frozenset({"notify_javier"}))
    assert notify.calls == []                                     # the effect never happened
    assert r["pending"] == [{"tool": "notify_javier", "arguments": {"message": "Hire this person"}}]
    assert "confirmation" in r["steps"][0]["result"]["error"]


# ---- misuse case 6: the unsupported claim (behavior 22) -----------------------------------------
def test_an_answer_naming_a_sha_and_date_the_tool_never_returned_is_replaced():
    r, _, _ = go([tool_call("recent_commits", '{"repo": "javieromolopez/TP1"}'),
                  answer("On November 12 Javier pushed 9f8e7d6, which added a login page.")])
    assert r["stopped_by"] == "claim_check" and r["answer"] == CLAIM_SENTENCE
    problems = " ".join(r["check"]["unsupported"])
    assert "9f8e7d6" in problems and "November 12" in problems
    assert "login page" in r["steps"][-1]["answer"]               # the model's text is kept in the trace


def test_check_accepts_what_the_tool_returned():
    steps = [{"tool": "recent_commits", "result": TP1}]
    assert check_answer("On Nov 9 (a1b2c3d) and 2026-11-02 Javier worked on TP1.", steps)["supported"]


def test_check_flags_a_commit_claim_when_no_commits_came_back():
    steps = [{"tool": "recent_commits", "result": {"error": "no public repository named 'x'", "exists": False}}]
    assert not check_answer("Yesterday he committed a fix to the deploy script.", steps)["supported"]
    assert not check_answer("He pushed changes today.", [])["supported"]
    assert check_answer("I couldn't find that repository, so I can't say.", steps)["supported"]


# ---- GitHub unavailable (behavior 21) ------------------------------------------------------------
def test_github_unavailable_stops_the_loop_with_the_programs_sentence():
    down = Stub(result={"error": "GitHub rate limit reached", "unavailable": True})
    r, client, _ = go([tool_call("recent_commits", '{"repo": "javieromolopez/TP1"}')], stub=down)
    assert len(client.sent) == 1                                  # no second chat call
    assert r["stopped_by"] == "github_unavailable" and r["answer"] == GITHUB_DOWN_SENTENCE
    assert r["steps"][0]["result"]["unavailable"] is True         # recorded in the trace


# ---- cost (behavior 26) --------------------------------------------------------------------------
def test_cost_adds_up_every_chat_call():
    r, _, _ = go([tool_call("recent_commits", '{"repo": "javieromolopez/TP1"}'), answer("ok")])
    assert abs(r["cost"] - 0.0002) < 1e-9
