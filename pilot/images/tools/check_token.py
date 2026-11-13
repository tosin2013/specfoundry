"""Verify the publisher token's scope without printing it (contracts/config.md).

Runs with PILOT_SCM_TOKEN in its own environment only (a child process; the orchestrator
never holds the value). Prints one JSON line: {ok, login, repo_push, canary_push, expires, problems}.

Write access is tested with a side-effect-free *write probe*: creating an unreferenced git blob
(POST /repos/{repo}/git/blobs). It succeeds only if the token can write the repository; the
orphan blob is invisible and garbage-collected. The `permissions` field of GET /repos is NOT
used to decide, because for a public repository it reflects the account's rights, not the
fine-grained token's (found 2026-11-13 when the specfoundry repo became public).

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


PROBE = {"content": "specfoundry publisher token scope probe (unreferenced blob)", "encoding": "utf-8"}


def get(path: str, token: str, method: str = "GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
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
    if st != 200:
        problems.append(f"cannot read {repo} (HTTP {st})")
    st_w, _, _ = get(f"/repos/{repo}/git/blobs", token, "POST", PROBE)
    repo_push = st_w == 201
    if st == 200 and not repo_push:
        problems.append(f"no write access to {repo} (write probe HTTP {st_w}; needs Contents: read and write)")
    st, r, _ = get(f"/repos/{repo}/pulls?state=all&per_page=1", token)
    if st != 200:
        problems.append(f"cannot list pull requests on {repo} (needs Pull requests: read and write)")
    canary_push = None
    if canary:
        st_c, _, _ = get(f"/repos/{canary}/git/blobs", token, "POST", PROBE)
        canary_push = st_c == 201
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
