"""The tool loop: the model asks, our code decides, the model answers from what it got back.

One run() is one visitor question. Each step is one billed chat call; a tool request costs another
call to deliver the result. The loop ends when the model answers without asking for a tool, at the
step cap, when GitHub is unavailable, or with the claim check's sentence when the answer claims
something the tools did not return. Spec "Week 8: one tool", behaviors 16, 19-24, 26.

    python -m tools.loop "What has Javier been committing to TP1 lately?" [--model M]
"""
import argparse
import json
import os
import time

from tools.check import check_answer
from tools.github import TOOL, owner_problem, recent_commits

DEFAULT_MODEL = os.environ.get("CHAT_MODEL", "minimax/minimax-m3")
# MiMo spends its whole budget on hidden reasoning unless it is off (Week 5); M3 needs it on.
REASONING = {"xiaomi/mimo-v2.6-flash": {"enabled": False}}
MAX_TOOL_CALLS = 4

CAP_TEMPLATE = "I couldn't finish answering that in {n} steps. Please ask a narrower question."
CAP_SENTENCE = CAP_TEMPLATE.format(n=4)           # at the default cap
GITHUB_DOWN_SENTENCE = ("I couldn't reach GitHub just now, so I can't say what Javier has committed "
                        "recently. Please ask again in a little while.")
CLAIM_SENTENCE = ("I can only tell you about commits I actually found on GitHub, and I couldn't back "
                  "that answer up. Try asking about one of Javier's repositories by name.")


# ---- the decision: plain code, no model ---------------------------------------------------------
def validate(name: str, args, schemas=(TOOL,)) -> str | None:
    """Every problem with a request, in one message, or None if it may run."""
    schema = next((t["function"]["parameters"] for t in schemas if t["function"]["name"] == name), None)
    if schema is None:
        names = ", ".join(t["function"]["name"] for t in schemas)
        return f"unknown tool {name!r}; the only tool{'s are' if len(schemas) > 1 else ' is'} {names}"
    if not isinstance(args, dict):
        return "arguments must be a JSON object"
    props, problems = schema["properties"], []
    problems += [f"unexpected argument {k!r}" for k in args if k not in props]
    problems += [f"missing required argument {k!r}" for k in schema.get("required", []) if k not in args]
    for key, val in args.items():
        spec = props.get(key)
        if spec is None:
            continue
        if spec["type"] == "string" and not isinstance(val, str):
            problems.append(f"argument {key!r} must be a string, got {type(val).__name__}")
        if spec["type"] == "integer":
            if isinstance(val, bool) or not isinstance(val, int):
                problems.append(f"argument {key!r} must be an integer, got {type(val).__name__}")
            elif not spec.get("minimum", val) <= val <= spec.get("maximum", val):
                problems.append(f"argument {key!r} must be from {spec['minimum']} to {spec['maximum']}, got {val}")
    if name == "recent_commits" and isinstance(args.get("repo"), str):
        problems += [p for p in [owner_problem(args["repo"])] if p]
    if problems:
        hint = '; send {"repo": "javieromolopez/<name>"}' if name == "recent_commits" else ""
        return "; ".join(problems) + hint
    return None


def run_tool(name: str, arguments, functions=None, schemas=(TOOL,), side_effects=frozenset()) -> dict:
    """What the loop calls for every request. Never raises on a bad request: the problem goes back
    to the model as the tool's result."""
    functions = {"recent_commits": recent_commits} if functions is None else functions
    if isinstance(arguments, str):
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError as e:
            return {"error": f"arguments were not valid JSON ({e.msg}); send a JSON object"}
    else:
        args = arguments
    problem = validate(name, args, schemas)
    if problem:
        return {"error": problem}
    if name in side_effects:
        return {"error": f"{name} needs a person's confirmation first; it has not been run",
                "pending": {"tool": name, "arguments": args}}
    if name not in functions:
        return {"error": f"tool {name!r} is not available"}
    return functions[name](**args)


# ---- the loop -----------------------------------------------------------------------------------
def run(question: str, system: str, model: str = DEFAULT_MODEL, max_steps: int = 4, client=None,
        functions=None, side_effects=frozenset(), tools=None) -> dict:
    """Returns {answer, stopped_by, steps, calls, pending, cost, seconds, check}."""
    tools = tools or [TOOL]
    if client is None:
        from openrouter import OpenRouter
        client = OpenRouter(api_key=os.environ["OPENROUTER_API_KEY"],
                            timeout_ms=int(os.environ.get("CHAT_TIMEOUT_MS", "120000")))
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    steps, pending, cost, ran, t_start = [], [], 0.0, 0, time.time()

    def result(answer, stopped_by):
        check = check_answer(answer, steps) if stopped_by == "answer" else {"supported": True, "unsupported": []}
        if not check["supported"]:
            answer, stopped_by = CLAIM_SENTENCE, "claim_check"
        return {"answer": answer, "stopped_by": stopped_by, "steps": steps,
                "calls": [s["tool"] for s in steps if "tool" in s], "pending": pending,
                "cost": round(cost, 6), "seconds": round(time.time() - t_start, 2), "check": check}

    for step in range(1, max_steps + 1):
        t0 = time.time()
        kwargs = {"model": model, "messages": messages, "tools": tools, "max_tokens": 1500}
        if model in REASONING:
            kwargs["reasoning"] = REASONING[model]
        c = client.chat.send(**kwargs)
        cost += getattr(c.usage, "cost", None) or 0.0
        msg = c.choices[0].message
        requests = msg.tool_calls or []
        if not requests:                                         # the model answered
            text = (msg.content or "").strip() or (
                f"I couldn't put an answer together (the model stopped: {c.choices[0].finish_reason}). "
                "Please ask again.")
            steps.append({"step": step, "answer": text, "finish": c.choices[0].finish_reason,
                          "seconds": round(time.time() - t0, 2)})
            return result(text, "answer")
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": tc.id, "type": "function",
                                         "function": {"name": tc.function.name,
                                                      "arguments": tc.function.arguments}}
                                        for tc in requests]})
        unavailable = False
        for tc in requests:
            if ran >= MAX_TOOL_CALLS:
                out = {"error": f"tool call limit reached ({MAX_TOOL_CALLS} per question); "
                                "answer from the results you have"}
            else:
                out = run_tool(tc.function.name, tc.function.arguments, functions,
                               tuple(tools), side_effects)
                ran += 1
            if "pending" in out:
                pending.append(out["pending"])
            unavailable = unavailable or out.get("unavailable") is True
            steps.append({"step": step, "tool": tc.function.name, "arguments": tc.function.arguments,
                          "result": out, "seconds": round(time.time() - t0, 2)})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out)})
        if unavailable:                                          # behavior 21: the program answers
            return result(GITHUB_DOWN_SENTENCE, "github_unavailable")
    return result(CAP_TEMPLATE.format(n=max_steps), "cap")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "voice"))
    from server import SYSTEM  # the chatbot's own prompt
    r = run(a.question, SYSTEM, a.model)
    for s in r["steps"]:
        if "tool" in s:
            print(f"step {s['step']}  {s['tool']}({s['arguments']})  ->  {json.dumps(s['result'])[:160]}")
        else:
            print(f"step {s['step']}  answer  [finish={s['finish']}]  {s['answer'][:160]}")
    print(f"\n{r['answer']}\n\nstopped_by={r['stopped_by']} calls={r['calls']} cost=${r['cost']:.6f} "
          f"seconds={r['seconds']} check={r['check']}")


if __name__ == "__main__":
    main()
