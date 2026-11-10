# Intent: tools

## Goal
The portfolio chatbot gets one real tool, `recent_commits`, so it can answer "what has Javier been working on lately?" from his actual GitHub history instead of guessing. The model only asks for the tool; our code validates every request, runs it or refuses it, and the chatbot never claims a commit the tool did not return.

## Who it is for
Recruiters, engineering managers, and classmates visiting the portfolio. Today the chatbot knows only the static `profile.json`, so a question about recent work gets "I don't know", or the visitor has to dig through GitHub themselves.

## Constraints
- **Tool:** `recent_commits(repo, count)`: the last few commits (date, short sha, first line of the message) of one public repository, from GitHub's REST API.
- **Only Javier's repositories.** Any `repo` not under `javieromolopez/` is refused in code, and the refusal goes back to the model as a result.
- **The model picks the repository** from the `repo` fields in `profile.json`, and may call the tool more than once. The program never chooses a repository the model did not ask for.
- **The model never runs anything.** Arguments are parsed and validated in code against the schema; a bad call, an unknown tool, a non-existent repository, or a repository that is not Javier's goes back to the model as an error result it can read and correct from, never as an exception.
- **GitHub unavailable** (rate limit, timeout, server error): the error is recorded in the trace as a tool result, the loop stops, and the visitor gets the program's fixed sentence: *"I couldn't reach GitHub just now, so I can't say what Javier has committed recently. Please ask again in a little while."*
- **Step cap of 4.** When the cap trips, the answer is the program's sentence, not the model's.
- **No invented claims.** An answer that names a commit, date, or repository the tool did not return is flagged by plain code.
- **Language:** Python, next to the existing `voice/` answer function, so the typed and voice paths both use the tool. The Java chatbot replaces it before November 30.
- **Models:** the class model `minimax/minimax-m3` (the chatbot's model now) and a comparison model with tool support; both are named in the spec.
- **Cost ceiling:** under 1 cent per visitor question, tool calls included. The eval records the real cost per question.
- **Secrets:** no key in the repository. `OPENROUTER_API_KEY` from the environment; an optional `GITHUB_TOKEN` from the environment raises GitHub's rate limit and is never committed.
- **Tests:** the misuse cases are tested with a scripted fake model and no key; the billed eval is separate and skipped without a key.

## Not in scope
- Any tool with a side effect (sending email, writing an outbox). The side-effect rule is still specified and tested, but no real side-effect tool ships.
- Private repositories, other people's repositories, issues, pull requests, or code contents.
- Caching GitHub responses or a fallback when GitHub is down beyond the fixed sentence.
- A second tool (only as an "if you finish early" extra).

## Success looks like
1. Asking "What have you been working on lately in TP1?" returns an answer that mentions only commits the tool returned, and the trace shows the call and its result.
2. Asking about a repository Javier does not have, or someone else's repository, gets an honest "no such repository" (or "not Javier's"), never invented commits.
3. Asking a question the profile already answers ("Do you know Java?") is answered without calling the tool, or the extra call shows in the eval's cost.

## Open questions
- Which comparison model (with tool support) to run the eval on: settled in the spec.

**Approved by:** Javier Romo, November 10, 2026
