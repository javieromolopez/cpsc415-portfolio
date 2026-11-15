"""recent_commits: the last few commits of one of Javier's public GitHub repositories.

The schema (TOOL) is what the model sees. The function is what our code runs, only after the loop
has validated the request. It never raises: every failure comes back as a result dict the model
(or the loop) can read. Spec behaviors 15, 17, 18, 21.

    python -m tools.github javieromolopez/TP1
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

OWNER = "javieromolopez"
REPO_RE = re.compile(rf"{OWNER}/[A-Za-z0-9_.-]+")

TOOL = {"type": "function", "function": {
    "name": "recent_commits",
    "description": "The most recent commits in one of Javier's public GitHub repositories. Use this "
                   "before saying anything about what Javier has worked on lately or committed. The "
                   "repository must be one listed in the profile, written as javieromolopez/<name>.",
    "parameters": {"type": "object",
                   "properties": {"repo": {"type": "string",
                                           "description": "javieromolopez/<name>, for example javieromolopez/TP1"},
                                  "count": {"type": "integer", "minimum": 1, "maximum": 10,
                                            "description": "How many commits, 1 to 10; default 5"}},
                   "required": ["repo"], "additionalProperties": False}}}


def owner_problem(repo: str) -> str | None:
    """Only Javier's repositories; no path tricks (".." is refused)."""
    if not REPO_RE.fullmatch(repo) or ".." in repo:
        return f"only {OWNER}/<name> repositories can be read; got {repo!r}"
    return None


def recent_commits(repo: str, count: int = 5) -> dict:
    problem = owner_problem(repo)
    if problem:
        return {"error": problem}
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/commits?per_page={count}",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "cpsc415-portfolio-chatbot"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": f"no public repository named {repo!r}", "exists": False}
        if e.code in (403, 429):
            return {"error": "GitHub rate limit reached", "unavailable": True}
        if e.code >= 500:
            return {"error": f"GitHub answered {e.code}", "unavailable": True}
        return {"error": f"GitHub answered {e.code}"}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"error": f"could not reach GitHub: {e}", "unavailable": True}
    return {"repo": repo, "commits": [{"sha": c["sha"][:7], "date": c["commit"]["author"]["date"][:10],
                                       "message": c["commit"]["message"].splitlines()[0][:100]}
                                      for c in data]}


if __name__ == "__main__":
    print(json.dumps(recent_commits(sys.argv[1] if len(sys.argv) > 1 else f"{OWNER}/TP1"), indent=1))
