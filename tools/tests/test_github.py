"""No-key, no-network tests for recent_commits: urllib's urlopen is replaced by a fake that answers
the way GitHub does (behaviors 17, 18, 21 in spec.md)."""
import io
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from tools import github
from tools.github import recent_commits

API = [{"sha": "a1b2c3d4e5f60718", "commit": {"author": {"date": "2026-11-09T19:14:08Z"},
                                               "message": "Critic: read the image\n\nLonger body"}},
       {"sha": "0f1e2d3c4b5a6978", "commit": {"author": {"date": "2026-11-02T10:00:00Z"},
                                               "message": "Eval: three repeats"}}]


class Fake:
    def __init__(self, reply):
        self.reply, self.urls = reply, []

    def __call__(self, req, timeout=None):
        self.urls.append(req.full_url)
        if isinstance(self.reply, BaseException):
            raise self.reply
        return io.BytesIO(json.dumps(self.reply).encode())


def http_error(code):
    return urllib.error.HTTPError("https://api.github.com/x", code, "err", {}, io.BytesIO(b"{}"))


@pytest.fixture
def fake(monkeypatch):
    def install(reply):
        f = Fake(reply)
        monkeypatch.setattr(github.urllib.request, "urlopen", f)
        return f
    return install


def test_commits_come_back_short_with_date_and_first_line(fake):
    f = fake(API)
    r = recent_commits("javieromolopez/TP1", 2)
    assert r == {"repo": "javieromolopez/TP1", "commits": [
        {"sha": "a1b2c3d", "date": "2026-11-09", "message": "Critic: read the image"},
        {"sha": "0f1e2d3", "date": "2026-11-02", "message": "Eval: three repeats"}]}
    assert f.urls == ["https://api.github.com/repos/javieromolopez/TP1/commits?per_page=2"]


def test_a_repository_that_does_not_exist_says_so(fake):
    fake(http_error(404))
    r = recent_commits("javieromolopez/kubernetes-lab")
    assert r["exists"] is False and "no public repository named" in r["error"]
    assert "unavailable" not in r


@pytest.mark.parametrize("failure", [http_error(403), http_error(429), http_error(502),
                                     urllib.error.URLError("no route"), TimeoutError("timed out")])
def test_github_unavailable_is_a_result_marked_unavailable(fake, failure):
    fake(failure)
    r = recent_commits("javieromolopez/TP1")
    assert r["unavailable"] is True and r["error"]


def test_another_owner_is_refused_before_any_request(fake):
    f = fake(API)
    assert "only javieromolopez/<name>" in recent_commits("kousen/ai-integration-course")["error"]
    assert "only javieromolopez/<name>" in recent_commits("javieromolopez/../secrets")["error"]
    assert f.urls == []
