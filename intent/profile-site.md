# Intent: profile-site

<!-- A small AI-enabled personal profile site. The chatbot answers a single
     visitor question — "should we work together?" — by reasoning strictly
     over a structured profile.json, never fabricating skills, and clearly
     distinguishing shipped work from what is currently being learned. -->

## Goal
A small, accessible website hosting a chatbot that answers one visitor question — *"should we work together?"* — by reasoning strictly over a structured `profile.json` file, never fabricating skills, and clearly distinguishing what has shipped from what is currently being learned.

## Who it is for
- **Primary: technical recruiters and engineering managers** evaluating candidates for junior backend Java roles. Today they have to read a long CV or scrape GitHub to judge fit.
- **Secondary: CS classmates** looking for a hackathon or course-project partner for backend-heavy or AI-integration work.

Both audiences need the same question answered honestly at speed, and a chatbot that quotes the profile is faster and more consistent than a hand-written cover letter.

## Constraints
- **Language:** Java (JDK 17+) with Jackson for JSON. No other external dependencies unless explicitly approved (per `CLAUDE.md`).
- **Model:** Single model — `xiaomi/mimo-v2.6-flash` via the OpenRouter API. Chosen because the Week 3 classifier lab showed it holds a strict JSON schema with ~40% fewer prompt tokens than `minimax/minimax-m3`, and this chatbot's job is faithful summarization rather than deep reasoning.
- **Architecture:** Single-model only. **No** secondary reviewer model. Multi-agent orchestration is on the "not yet" list and is deferred until basic backend AI integration is solid.
- **Runtime:** A tiny hand-written Java HTTP server serves a vanilla HTML/JS chat page and forwards requests to the model. No frontend frameworks — React/Vue are on the "not yet" list.
- **Cost ceiling:** Under $5 for the entire semester. The chosen model is fractions of a cent per request, leaving comfortable headroom for testing without risking API lockouts.
- **Source data:** A single static `profile.json` file. No database, no live state, no integrations beyond the model API.
- **Project shape:** Solo developer, matching every prior shipped project. No team collaboration is assumed in the build.
- **Career positioning (lives in `profile.json`, not in code):** Junior undergrad studying Data Science. Open to internships, short-term collaborations, hackathons, backend Java projects, **and** frontend-heavy work (open to learning, not claiming it as shipped). Not open to full-time roles before graduation or long-term commitments this semester.

## Not in scope
- User accounts, logins, or analytics tracking.
- Any database — the chatbot reads only the static `profile.json`.
- A blog, project gallery, or "download CV" button.
- "Live" elements such as current calendar availability.
- A mobile app or internationalization (i18n).
- Multi-agent orchestration, RAG over external knowledge bases, or any other feature currently on the "not yet" learning list.
- Frontend frameworks (React, Vue, etc.) — the chat UI stays plain HTML/CSS/JS.

## Success looks like
Three checks I can perform by hand:

1. **The Not-Yet Check.** Asking *"Can you build a React frontend?"* or *"Can you do advanced Python data science?"* produces a response that explicitly says those skills are on the "not yet" learning list — and, for the frontend case, adds that Javier is open to learning it as part of a collaboration (not a flat "no").
2. **The Fabrication Check.** Asking about a skill that appears nowhere in `profile.json` (e.g., *"Do you know C# or AWS?"*) produces a refusal to claim it and a clear statement that it is not part of the profile.
3. **The Shipped-Work Check.** Asking *"What did you do on the Disaster Response System?"* returns an accurate description of the solo role and the specific Java data structures used, without inventing team members, additional features, or technologies that are not in the profile.

## Open questions
- **Profile schema.** The exact field set in `profile.json` (projects, tech stack, "not yet" list, open-to / not-open-to, audience examples, audience "wasted-visit" notes) is a spec-level decision and will be settled when `spec.md` is written.
- **Frontend routing rule.** When asked about a "not yet" skill like React, the chatbot must (a) state it is on the not-yet list, *and* (b) add that Javier is open to frontend-heavy work because he learns fast. Whether this rule is enforced by prompt structure, by a small intent classifier on the user query, or by hard-coded rules in the server is a spec decision.
- **Evaluation suite.** A concrete eval covering the three Success checks above (plus adversarial cases) needs to be designed in the spec stage. The course's `*Eval.java` test convention is the likely home for it.

**Approved by:** Javier Romo, October 4, 2026
