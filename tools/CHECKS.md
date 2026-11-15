# Week 8 checks: one real tool

The tool is `recent_commits(repo, count)` in `tools/github.py`, run by the loop in `tools/loop.py` and wired into `answer()` in `voice/server.py`, so the typed path (`/api/ask`) and the voice path (`/api/voice`) both use it. The profile in the system prompt is Javier's own (`voice/profile.json`, replaced on November 10). The tool adds the one thing the profile does not have: what Javier has committed lately.

## No-key tests

`python -m pytest tools/tests/test_loop.py tools/tests/test_github.py -v`: **24 passed in 0.2 s**, no key, no network. They were committed failing first (`779aba1`, "the loop's misuse cases (failing, no code yet)": both files failed at import, because `tools/check.py` did not exist). The code that turned them green came next (`87f9144`). The Week 7 checker tests still pass (38 in all).

## The eval: five questions on two models

`python -m pytest tools/tests/test_eval.py -v -s`, run November 15, 2026. The chatbot's own system prompt, the real tool, and live GitHub. The raw lines, with every tool result and the full answers, are in `tools/eval-results.jsonl`. "Steps" counts chat calls. A pass means:
- the loop ended with the model's answer, not the cap, GitHub down, or the claim check;
- the required repositories were asked for;
- the must-say and must-not-say words held;
- the claim check found nothing unsupported.

| # | Question | Model | Tools called | Steps | Result | Cost | Seconds |
|---|---|---|---|---|---|---|---|
| 1 | What has Javier been committing to TP1 lately? | minimax-m3 | `recent_commits(TP1, 5)` | 2 | pass | $0.000883 | 5.2 |
| 1 | | mimo-v2.6-flash | `recent_commits(TP1)` | 2 | pass | $0.000454 | 4.4 |
| 2 | What are the latest commits in Javier's Kubernetes repository? | minimax-m3 | none | 1 | pass | $0.000209 | 1.3 |
| 2 | | mimo-v2.6-flash | none | 1 | pass | $0.000247 | 2.3 |
| 3 | Does Javier know Java? | minimax-m3 | none | 1 | pass | $0.000220 | 1.5 |
| 3 | | mimo-v2.6-flash | none | 1 | pass | $0.000233 | 2.4 |
| 4 | What did Javier commit yesterday? | minimax-m3 | `recent_commits(TP1, 5)` | 2 | pass (see below) | $0.000597 | 4.0 |
| 4 | | mimo-v2.6-flash | `recent_commits(TP1)`, `recent_commits(cpsc415-week05)` | 2 | pass | $0.000237 | 20.4 |
| 5 | What changed most recently in his receipt reader and in his RAG project? | minimax-m3 | `recent_commits(cpsc415-week05)`, `recent_commits(cpsc415-week04)` | 2 | pass | $0.000876 | 8.3 |
| 5 | | mimo-v2.6-flash | `recent_commits(cpsc415-week05, 5)`, `recent_commits(cpsc415-week04, 5)` | 2 | pass | $0.000145 | 6.9 |

**10 of 10 passed** under the checks in code. The whole eval cost **$0.0041** (minimax-m3 $0.0028, mimo $0.0013).

What the table does not show:
- **Question 2: neither model called the tool.** Both answered from the profile that there is no Kubernetes repository. That is a correct answer, but it means the 404 path (behavior 18) was never reached by a real model. Only `test_github.py` covers it.
- **Question 4 passed the check but is misleading on minimax-m3.** It described the latest TP1 commits (all November 2) under the question "what did he commit yesterday?" without saying that none of them were from yesterday. MiMo said plainly that the newest commits were from November 2 and that it couldn't confirm "yesterday". See *What the check cannot catch*.
- **Question 5: both models asked for both repositories in one reply** (parallel `tool_calls`), so two tool calls still took only two chat calls.
- In a development run of question 1 before the eval, minimax-m3 asked for TP1 twice: first with the default count, then again with `count: 10`, for the same answer. That made 3 steps and cost $0.001277, the most expensive question I saw.

### Totals
- **Cost per question with a tool call:** **$0.00053** on average (6 questions, $0.000145 to $0.000883).
- **Cost per question without a tool call:** **$0.00023** on average (4 questions, $0.000209 to $0.000247).
- **Most steps any question took:** **2** in the eval, and 3 in the development run above. The step cap of 4 was never reached by a real model. The limit of 4 tool calls per question was reached once, by hand (see *A real model hits the tool-call limit*).

## Misuse cases

| Misuse case | The test that covers it | Did a real model do it in the eval? |
|---|---|---|
| Single shot (the result goes back as a `tool` message with the right `tool_call_id`) | `test_single_shot_result_goes_back_as_a_tool_message_with_the_right_id`, `test_the_schema_is_sent_with_every_request` | Yes, the normal case: question 1 on both models, `recent_commits({"repo": "javieromolopez/TP1"})`, then the answer in step 2. |
| Bad arguments (an error result, the loop continues, and the corrected call runs) | `test_bad_arguments_get_an_error_result_and_the_loop_continues`, plus the JSON, count, type, and owner edge tests | No. Every real call had valid arguments in the full `javieromolopez/<name>` form; the system prompt's "written exactly as it appears there" was enough. |
| Unknown tool (an error result, nothing runs) | `test_unknown_tool_gets_an_error_result_and_nothing_runs` | No. |
| Endless caller (stopped by the cap; the answer is the program's) | `test_endless_caller_is_stopped_by_the_cap_and_the_answer_is_the_programs`, `test_one_reply_with_six_calls_runs_only_four` | Not in the eval, but **yes, by hand on November 15** (below): minimax-m3 asked for five repositories in one reply, and the limit of 4 stopped the fifth. Also in the development run: minimax-m3 repeated the TP1 call with `count: 10` and then answered in step 3. |
| Side effect held (recorded as pending, never run) | `test_a_side_effect_is_recorded_as_pending_and_does_not_happen` (a test-only `notify_javier` tool) | Not applicable: `recent_commits` is read-only and no side-effect tool ships. |
| Unsupported claim (flagged, and the visitor gets the program's sentence) | `test_an_answer_naming_a_sha_and_date_the_tool_never_returned_is_replaced`, `test_check_flags_a_commit_claim_when_no_commits_came_back`, `test_check_accepts_what_the_tool_returned` | No answer was flagged. Question 4 on minimax-m3 is a misleading answer the check let through (below). |

### A real model hits the tool-call limit (voice, November 15)

I tested the finished chatbot on the voice page (`python voice/server.py`, `http://localhost:8000`), on minimax-m3. Whisper transcribed my question as "What has Javier been working on? Lately, Yeah." The trace the page showed:

```text
Tools (stopped by answer):
  recent_commits({"repo":"javieromolopez/TP1"}) -> 5 commits
  recent_commits({"repo":"javieromolopez/cpsc415-week05"}) -> 5 commits
  recent_commits({"repo":"javieromolopez/cpsc415-week04"}) -> 5 commits
  recent_commits({"count":5,"repo":"javieromolopez/cpsc415-week03"}) -> 5 commits
  recent_commits({"count":5,"repo":"javieromolopez/cpsc415-week02"}) -> error: tool call limit reached (4 per question); answer from the results you have
```

- **The limit did its job.** All five calls came in one reply, so the step cap alone (which counts chat calls) would have let all five reach GitHub. The fifth was refused in code, and the model answered from the four results in the next step.
- **This is the gap my second plan question found.** The limit came from that question; the eval never triggered it, but a vague question on a real model did.
- **The claim check passed, correctly.** The answer named no commit ID or date, and what it described matches the four results.
- **One sentence was muddled anyway.** The answer included "The receipts aside, these are all model-backed tools…", but the receipt reader is model-backed too. No rule here can catch that (see below).
- **Cost:** chat **$0.0022**, the most of any question so far but still under the 1-cent ceiling. Speech $0.0099, because the answer was three long sentences. Transcription $0.00002. **Total $0.0122** for the turn, in 16 seconds (6.7 + 7.7 + 1.6).

## What the check cannot catch

The claim check (`tools/check.py`) knows three things: commit IDs, dates, and the words "committed" or "pushed" when nothing came back. It cannot judge **what an answer says about real commits**.

- **Question 4 on minimax-m3, "What did Javier commit yesterday?":** the model listed the latest TP1 commits as the answer. Every word was supported, and no date was named, so no rule fired. But a visitor would reasonably hear "here is what he committed yesterday", and the newest commit was from November 2, twelve days before "yesterday". The check compares dates the answer *names*; it cannot notice a date the answer *implies* by leaving it out.
- **A wrong description of a real commit:** "fixed the critic's crash" for a commit whose message is "Critic: read the image, not the prompt" names no ID and no date, so it passes. Only something that reads both the commit message and the sentence could notice.
- **The default branch only:** GitHub's commits endpoint reads the default branch. GitHub shows TP1 as pushed on November 9, but its default branch's newest commit is from November 2. The tool, the model, and the check all agree on November 2, and none of them can know about work on other branches.

What would catch these:
- **A stricter prompt** ("if the question names a day, say whether any commit is from that day") would likely fix question 4 on minimax-m3, but nothing proves it does.
- **A second model as a judge,** given the question, the tool results and the answer, asked "does the answer imply anything the results do not show?". It could catch the implied date and the wrong description, at the cost of one more chat call per question, and it can be wrong too.
- **A person** reading a sample of answers against `eval-results.jsonl`, which keeps every tool result for exactly that. That is how question 4 was found here.

## The cost of a tool

- **With a tool call:** $0.00053 per question on average, and $0.00128 for the worst question I saw (3 steps). **Without one:** $0.00023. A question that uses the tool costs about **2.3 times** as much, because the result has to go back to the model in a second chat call carrying the whole prompt again.
- **Against the ceiling:** the worst eval question used about an eighth of the 1-cent ceiling. The worst question overall was the voice test with four tool calls: $0.0022 of chat, about a fifth of the ceiling. At the 4-step cap, a question costs at most four chat calls, about $0.002–0.004 on these models, still under the ceiling.
- **What it means for hosting:** a voice turn was about $0.005 in Week 7, almost all of it the speech. The tool adds about $0.0003 to the chat part, roughly 6% of a voice turn, and doubles the cost of a typed turn (still well under a tenth of a cent). For the hosting decision before November 30, the per-turn figure is about **$0.0006 typed with a tool, and $0.005–0.006 spoken**. MiMo was cheaper on every question with a tool ($0.00015–0.00045 against $0.0006–0.0009) but took 20 seconds on question 4. GitHub costs nothing, but allows 60 requests an hour per server address without a token. A hosted chatbot that gets more traffic needs `GITHUB_TOKEN` (5,000 an hour) or a short cache.

## Linter

`ruff check tools voice` with the repository's ruff 0.17.2 settings. The first run on the new code found **9** problems:
- 3 × FURB167: `re.I` instead of `re.IGNORECASE` in `check.py`;
- 2 × UP041: `socket.timeout` instead of `TimeoutError` in `github.py` and its test;
- 2 × I001: import order in `loop.py` and `test_loop.py`;
- 2 × RUF059: unpacked variables never used in `test_loop.py`.

Wiring the tool into the chatbot and adding the eval added one I001 each, in `voice/server.py` and `test_eval.py`. All were fixed with `ruff check --fix` (the two RUF059s needed `--unsafe-fixes`, which only renamed the unused variables to start with `_`). The no-key tests passed again after each fix. Final run: **All checks passed!**
