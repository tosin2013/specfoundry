"""Verify the publisher token's scope without printing it (contracts/config.md).

Runs with PILOT_SCM_TOKEN in its own environment only (a child process; the orchestrator
never holds the value). Prints one JSON line: {ok, login, repo_push, canary_push, expires, problems}.

    check_token.py <fixture owner/name> <canary owner/name>

The canary is a repository the token must NOT be able to write (specfoundry's own origin).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def get(path: str, token: str):
    req = urllib.request.Request(API + path, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "specfoundry-pilot-token-check"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, None, dict(e.headers or {})


def check(token: str, repo: str, canary: str | None, get=get) -> dict:
    problems = []
    st, user, hdr = get("/user", token)
    login = (user or {}).get("login")
    if st != 200:
        problems.append(f"token rejected by GitHub (HTTP {st})")
    expires = hdr.get("github-authentication-token-expiration") or hdr.get("GitHub-Authentication-Token-Expiration")
    st, r, _ = get(f"/repos/{repo}", token)
    perms = (r or {}).get("permissions") or {}
    repo_push = bool(perms.get("push"))
    if st != 200:
        problems.append(f"cannot read {repo} (HTTP {st})")
    elif not repo_push:
        problems.append(f"no write access to {repo} (needs Contents: read and write)")
    st, r, _ = get(f"/repos/{repo}/pulls?state=all&per_page=1", token)
    if st != 200:
        problems.append(f"cannot list pull requests on {repo} (needs Pull requests: read and write)")
    canary_push = None
    if canary:
        st, r, _ = get(f"/repos/{canary}", token)
        canary_push = bool(((r or {}).get("permissions") or {}).get("push")) if st == 200 else False
        if canary_push:
            problems.append(f"token can write {canary}: scope it to the fixture repo only")
    return {"ok": not problems, "login": login, "repo": repo, "repo_push": repo_push,
            "canary": canary, "canary_push": canary_push, "expires": expires, "problems": problems}


def main(argv) -> int:
    token = os.environ.get("PILOT_SCM_TOKEN", "")
    if not token:
        print(json.dumps({"ok": False, "problems": ["PILOT_SCM_TOKEN missing"]}))
        return 1
    res = check(token, argv[1], argv[2] if len(argv) > 2 and argv[2] else None)
    print(json.dumps(res))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
