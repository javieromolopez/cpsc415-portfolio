# Spec

<!-- The agent writes this from the approved intent. You validate it against the intent.
     If the spec and the intent disagree, the intent wins until you change the intent. -->

## Intent
This spec implements `intent/profile-site.md`.

## Components

### `profile.json` (data)
- **What it does:** Single static source of truth for everything the chatbot may say. Holds shipped projects, tech stack, "not yet" learning list, open-to / not-open-to collaboration boundaries, and the four example projects plus tech-stack facts collected during the interview.
- **Language:** JSON. **Why:** Trivial to parse with Jackson (the only approved JSON lib per `CLAUDE.md`), trivial to edit without code changes, and easy to diff in version control. A typed Java record mirrors its schema (see ProfileLoader below).
- **Model:** N/A — pure data.
- **Interfaces:** Read once at server startup. Reserialized into the system prompt on every chat request (small file, low cost). Schema:
  ```
  {
    "name": "Javier Romo",
    "career_stage": "Junior undergrad studying Data Science",
    "primary_language": "Java",
    "languages_claimed": ["Java", "vanilla HTML/CSS/JS"],
    "languages_not_claimed": ["Python (readable, basic scripting only)"],
    "shipped_projects": [
      { "name": "Support Message Classifier", "what": "...", "stack": ["Java", "Jackson", "OpenRouter"], "repo": "cpsc415-week03", "role": "solo", "when": "Fall 2026" },
      { "name": "Disaster Response Pipeline",  "what": "...", "stack": ["Java", "BST", "HashMap", "Max-Heap", "Undirected Graph"], "role": "solo", "when": "Spring 2026" },
      { "name": "Contacts App",                "what": "...", "stack": ["Java", "custom BST-backed ADT Map"], "role": "solo", "when": "Spring 2026" },
      { "name": "Lyrics Trainer",              "what": "...", "stack": ["HTML", "CSS", "vanilla JS"], "repo": "cpsc415-week01", "role": "solo (directed orclaude)", "when": "Sept 2026 (Week 1)" }
    ],
    "not_yet": [
      { "skill": "Python for Data Science", "depth": "DataCamp course, basic scripting only" },
      { "skill": "RAG",                      "depth": "starting Week 4 theory in AI Integration" },
      { "skill": "Multi-Agent Orchestration", "depth": "theoretical understanding, no .claude/agents/ yet" },
      { "skill": "Frontend Frameworks (React/Vue)", "depth": "intentionally deferred; vanilla HTML/JS shipped at small scale" }
    ],
    "open_to": [
      "internships",
      "short-term collaborations",
      "hackathon teammates",
      "backend Java projects",
      "frontend-heavy work (learning, not claiming as shipped)"
    ],
    "not_open_to": [
      "full-time roles before graduation",
      "long-term commitments this semester"
    ],
    "wasted_visit_notes": [
      "Recruiters evaluating senior/lead roles",
      "Visitors wanting heavy React/Vue shipped work or advanced Python data engineering"
    ]
  }
  ```
- **Dependencies:** None.

### ProfileLoader (Java)
- **What it does:** Reads `profile.json` from the working directory at server startup and parses it into a typed Java record (`Profile`). Fails fast on a missing file, a malformed JSON document, or a schema mismatch.
- **Language:** Java (JDK 17+). **Why:** Mandated by `CLAUDE.md`. Jackson is the only approved JSON library, so the choice is forced. Alternatives considered: Gson (unapproved dep), manual JSON parsing (reinvents Jackson), org.json (unapproved dep).
- **Model:** N/A.
- **Interfaces:**
  - `Profile load(Path source)` — throws `ProfileLoadException` with a human-readable cause on any failure.
  - `String toSystemPromptSection(Profile p)` — flattens the profile into a plain-text block for embedding in the system prompt.
- **Dependencies:** Jackson (`com.fasterxml.jackson.databind`).

### PromptBuilder (Java)
- **What it does:** Assembles the system and user messages sent to the model. Embeds the entire `profile.json` (flattened) into the system prompt so the model cannot drift outside it. Embeds the rules from the intent's Success checks directly in the system prompt — including the "not-yet means open-to-learning, not flat no" rule.
- **Language:** Java. **Why:** Keeps prompt logic version-controlled alongside the rest of the server and easy to unit-test without an HTTP call.
- **Model:** N/A — this component only *shapes* the prompt; it does not call the model.
- **Interfaces:**
  - `Prompt build(Profile p, String userQuestion)` — returns `{ system: String, user: String }`.
- **Dependencies:** ProfileLoader types only.

### ModelClient (Java)
- **What it does:** Sends a chat-completion request to the OpenRouter API and returns the model's text reply, or throws a typed exception on auth failure, rate limit, network error, or empty/refused response.
- **Language:** Java. **Why:** Mandated. Uses JDK's built-in `java.net.http.HttpClient` — no extra HTTP library needed. Alternatives considered: OkHttp (unapproved dep), Apache HttpClient (unapproved dep), manual `Socket` (reinvents HttpClient).
- **Model:** `xiaomi/mimo-v2.6-flash` via OpenRouter. **Why:** Compared against `minimax/minimax-m3` on a real task (the Week 3 support-message classifier lab). On that task, `mimo-v2.6-flash` held the strict JSON schema correctly and used ~40% fewer prompt tokens. Did not evaluate a frontier model (e.g., Claude Sonnet, GPT-4o class) because the chatbot's job is faithful summarization of a small static document, not reasoning — the spec calls for the cheapest model that is faithful, not the smartest. A frontier model would also blow the sub-$5/semester cost ceiling once a reviewer pattern is layered on later.
- **Interfaces:**
  - `String chat(String systemPrompt, String userPrompt)` — returns the assistant text.
  - Throws `AuthException` (401/403, including key-limit/quota), `RateLimitException` (429), `ModelRefusalException` (empty `content` or refusal-style finish), `TimeoutException`, `TransportException`.
- **Dependencies:** `java.net.http.HttpClient` (JDK built-in). Reads API key from `OPENROUTER_API_KEY` environment variable.

### ChatServer (Java)
- **What it does:** A minimal HTTP server. Serves the static chat UI at `GET /` and proxies chat messages at `POST /api/chat`. Stateless: every request re-sends the system prompt.
- **Language:** Java. **Why:** Mandated. Uses the JDK's built-in `com.sun.net.httpserver.HttpServer` — sufficient for a single-route server with one API endpoint. Alternatives considered: Spring Boot (unapproved dep, heavy), Javalin/Spark (unapproved deps), hand-rolled `ServerSocket` (reinvents `HttpServer`).
- **Model:** N/A — it orchestrates, the ModelClient holds the model.
- **Interfaces:**
  - `GET /` → returns `index.html` from the classpath.
  - `POST /api/chat` with JSON body `{"question": "..."}` → returns JSON `{"answer": "..."}` or `{"error": "<type>", "message": "<human-readable>"}` with appropriate HTTP status.
  - Listens on port 8080 by default; override with `--port` or `PORT` env var.
- **Dependencies:** JDK built-in `com.sun.net.httpserver.HttpServer`. ProfileLoader, PromptBuilder, ModelClient.

### Chat UI (HTML/CSS/JS)
- **What it does:** A single-page chat interface: a scrollable message list, an input box, and a Send button. Plain HTML/CSS/JS, served as `index.html` from the classpath. No frameworks, no build step.
- **Language:** HTML + CSS + vanilla JavaScript. **Why:** Per intent, frontend frameworks are on the "not yet" list. Vanilla is sufficient for one text input and one message list.
- **Model:** N/A.
- **Interfaces:** Loads from `GET /`. Posts user messages to `/api/chat`. Renders the response or a typed error message.
- **Dependencies:** None.

### Eval suite — `Eval.java`
- **What it does:** Runs the three Success checks from the intent plus adversarial cases. Designed to fail loudly if the chatbot fabricates or stops honoring the shipped-vs-aspirational rule.
- **Language:** Java. **Why:** Course convention (`*Eval.java` files live at the repo root per `CLAUDE.md`). Pinned here so the build stage has a fixed target.
- **Model:** Calls the real `ModelClient` (no mocking) so the eval exercises the actual prompt + model. Skipped automatically when `OPENROUTER_API_KEY` is unset, with a printed warning, so local builds don't fail for missing keys.
- **Interfaces:**
  - `public static void main(String[] args)` — runs all cases, prints `PASS` / `FAIL` per case, exits non-zero on any failure.
- **Dependencies:** ProfileLoader, PromptBuilder, ModelClient, Jackson.

## Behavior
Numbered requirements the tests will check.

1. **Boot succeeds when `profile.json` is valid and `OPENROUTER_API_KEY` is set.** Loader throws a clear error otherwise.
2. **`GET /` returns the chat UI HTML.**
3. **`POST /api/chat` with `{"question": "..."}` returns a non-empty assistant answer when the question is about a profile-listed topic.** (Shipped-Work Check.)
4. **`POST /api/chat` answering a question about a skill listed in `not_yet` returns a reply that (a) names the skill as on the "not yet" list and (b), for `Frontend Frameworks (React/Vue)`, adds that Javier is open to learning it as part of the collaboration — never a flat "no."** (Not-Yet Check.)
5. **`POST /api/chat` answering a question about a skill that appears nowhere in the profile (e.g., "Do you know C# or AWS?") returns a reply that explicitly says it is not part of the profile and does not claim it.** (Fabrication Check.)
6. **`POST /api/chat` answering "what did you do on the Disaster Response Pipeline?" names Java, custom BST/HashMap/Max-Heap/Undirected Graph, and the solo role, without inventing a team, additional features, or technologies not in the profile.** (Shipped-Work Check, specific case.)
7. **The system prompt sent to the model includes the entire flattened profile and the explicit grounding rules, so a downstream reviewer can audit what the model saw.**

## Failure handling
- **Malformed `profile.json`** (missing file, invalid JSON, schema mismatch): server fails fast at startup with the file path and the specific field that failed. Exit code 1.
- **Missing `OPENROUTER_API_KEY`:** server fails fast at startup with the env var name. Eval prints a skip notice and exits 0.
- **OpenRouter 401/403** (bad key, expired key, key-limit/quota): server returns HTTP 502 to the client with `{"error":"auth","message":"API key rejected — check OPENROUTER_API_KEY and any quota."}`. Logged once at startup if the key is rejected immediately.
- **OpenRouter 429** (rate limit): server returns HTTP 503 with `{"error":"rate_limit","message":"Model is rate-limited; try again shortly."}`.
- **Network / timeout:** server returns HTTP 502 with `{"error":"transport","message":"Could not reach the model."}`. Default timeout: 15 seconds per request.
- **Empty response or refusal-shaped finish from the model:** ModelClient throws `ModelRefusalException`; server returns HTTP 502 with `{"error":"model_refusal","message":"The model returned no answer."}`.
- **Hallucinated answer** (caught only by Eval, not at runtime): the Fabrication Check asserts the model's reply does not claim skills outside the profile. A failure here is a spec violation that must be fixed by editing the system prompt, not the code.
- **Bad input** to `/api/chat` (missing `question`, non-JSON body): server returns HTTP 400 with `{"error":"bad_request","message":"Expected JSON body with a 'question' field."}`.

## Cost estimate
- **Per request:** System prompt ≈ 500 tokens (flattened profile + rules); user message ≈ 50 tokens; model reply ≈ 200 tokens. Total ≈ 750 tokens.
- **Model price (Xiaomi mimo-v2.6-flash tier, fractions-of-a-cent claim):** roughly $0.10 per 1M input tokens, $0.30 per 1M output tokens is a conservative upper bound; the user's interview notes put real cost below this.
- **Per chat request:** ≤ $0.0002.
- **Eval suite:** ~20 cases × ≤ $0.0002 = ≤ $0.004 per run.
- **Semester projection:** 1,000 visitor chats + 50 eval runs ≈ $0.20, well under the $5 ceiling. The ceiling exists for safety margin against runaway testing, not because realistic use approaches it.

## Out of scope
Carried over from the intent, plus design-level exclusions:

- User accounts, logins, analytics.
- Any database — only `profile.json`.
- Blog, project gallery, "download CV" button.
- Live/calendar availability.
- Mobile app, i18n.
- Multi-agent orchestration or RAG.
- Frontend frameworks.
- Streaming responses (synchronous request/response is simpler and fine for short answers).
- Conversation memory across requests (each request is stateless; this also avoids storing visitor messages).
- Tool/function calling by the model (not needed; the profile is in the prompt).
- HTTPS / TLS termination (handled at deploy, not in this spec).
- Logging visitor messages to disk (analytics is out of scope; logs stay in memory and are not persisted).
