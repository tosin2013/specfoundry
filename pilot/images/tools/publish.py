"""Publisher (runs in the `pilot-publish` namespace only; research R8, FR-013-FR-016).

Inputs  /in/pr.json   {repo, head, base, base_revision, title, body, run_id, task}
        /in/change.bundle
        env PILOT_SCM_TOKEN (fine-grained, throwaway repo only), HTTPS_PROXY (scm-egress)
Output  stdout frame with result.json {number, url, head, draft, author, token_login, created}

There is deliberately no merge code path in this file.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

API = "https://api.github.com"


class GitHub:
    def __init__(self, token: str, api: str = API):
        self._token = token
        self.api = api

    def _req(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.api + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self._token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "specfoundry-pilot-publisher"})
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"null")

    def user_login(self) -> str:
        return self._req("GET", "/user")["login"]

    def open_prs(self, repo: str, owner: str, head: str) -> list:
        q = urllib.parse.urlencode({"head": f"{owner}:{head}", "state": "open"})
        return self._req("GET", f"/repos/{repo}/pulls?{q}")

    def create_draft_pr(self, repo: str, head: str, base: str, title: str, body: str) -> dict:
        return self._req("POST", f"/repos/{repo}/pulls",
                         {"title": title, "head": head, "base": base, "body": body, "draft": True})


def _summary(pr: dict, created: bool, token_login: str) -> dict:
    return {"number": pr["number"], "url": pr["html_url"], "head": pr["head"]["ref"], "draft": bool(pr.get("draft")),
            "author": pr["user"]["login"], "token_login": token_login, "created": created}


def publish(gh, push, spec: dict) -> dict:
    """Idempotent: an open PR for the head branch is recorded, never duplicated."""
    repo, head = spec["repo"], spec["head"]
    owner = repo.split("/")[0]
    login = gh.user_login()
    existing = gh.open_prs(repo, owner, head)
    if existing:
        return _summary(existing[0], False, login)
    push(spec)
    existing = gh.open_prs(repo, owner, head)  # a concurrent/previous call may have won
    if existing:
        return _summary(existing[0], False, login)
    pr = gh.create_draft_pr(repo, head, spec["base"], spec["title"], spec["body"])
    return _summary(pr, True, login)


def git_push(spec: dict, bundle: str = "/in/change.bundle") -> None:
    """Push base_revision + bundle to the head branch. The token reaches git only via GIT_ASKPASS."""
    with tempfile.TemporaryDirectory() as t:
        askpass = os.path.join(t, "askpass.sh")
        with open(askpass, "w") as f:
            f.write('#!/bin/sh\ncase "$1" in Username*) echo x-access-token;; *) printf %s "$PILOT_SCM_TOKEN";; esac\n')
        os.chmod(askpass, 0o700)
        env = {**os.environ, "GIT_ASKPASS": askpass, "GIT_TERMINAL_PROMPT": "0",
               "https_proxy": os.environ.get("HTTPS_PROXY", ""), "HOME": t}
        url = f"https://github.com/{spec['repo']}.git"
        repo = os.path.join(t, "repo")

        def g(*a):
            subprocess.run(["git", *a], cwd=repo if os.path.isdir(repo) else t, env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=sys.stderr)
        g("clone", "--quiet", "--branch", spec["base"], url, repo)
        g("cat-file", "-e", spec["base_revision"] + "^{commit}")
        g("fetch", "--quiet", bundle, "HEAD:refs/pilot/graded")
        g("push", "--quiet", "--force", "origin", f"refs/pilot/graded:refs/heads/{spec['head']}")


def main() -> int:
    sys.path.insert(0, "/usr/local/lib/pilot")
    import frame  # noqa: E402  (copied into the image)
    spec = json.load(open("/in/pr.json"))
    result = {"error": None}
    try:
        result = publish(GitHub(os.environ["PILOT_SCM_TOKEN"]), git_push, spec)
        result["error"] = None
    except Exception as e:  # noqa: BLE001
        result = {"error": f"{e.__class__.__name__}: {str(e)[:300]}"}
    out = os.path.join(tempfile.mkdtemp(), "result.json")
    with open(out, "w") as f:
        json.dump(result, f)
    frame.main(["emit", f"result.json={out}"])
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())
