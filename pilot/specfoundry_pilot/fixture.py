"""Throwaway fixture repo: fresh clones (read, operator auth) and reset (operator-approved write).

Host-side git writes use the operator's own `gh` login through a one-off credential helper
(`-c credential.helper=!gh auth git-credential`); no git config is changed and the
publisher token is never used here.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config, paths

GH_CRED = ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]


def git(*args, cwd=None, check=True, timeout=120) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *GH_CRED, *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[:500]}")
    return r


def gh(*args, check=True, timeout=60) -> subprocess.CompletedProcess:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[:500]}")
    return r


def url(repo: str) -> str:
    return f"https://github.com/{repo}.git"


def fresh_clone(repo: str, branch: str, depth: int | None = 1) -> tuple[Path, str]:
    """Clone the default branch into a new temp dir. Returns (path, HEAD sha). Caller deletes."""
    d = Path(tempfile.mkdtemp(prefix="pilot-fixture-"))
    args = ["clone", "--quiet", "--branch", branch]
    if depth:
        args += ["--depth", str(depth)]
    try:
        git(*args, url(repo), str(d))
        head = git("rev-parse", "HEAD", cwd=d).stdout.strip()
        return d, head
    except Exception:
        shutil.rmtree(d, ignore_errors=True)
        raise


def open_pilot_prs(repo: str) -> list[dict]:
    import json
    out = gh("pr", "list", "-R", repo, "--state", "open", "--json", "number,headRefName,url", "--limit", "200").stdout
    return [p for p in json.loads(out or "[]") if p["headRefName"].startswith("pilot/")]


def reset(cfg, yes: bool = False) -> int:
    config.repo_guard(cfg.repo, config.origin_repo())
    print(f"This force-resets {cfg.repo}@{cfg.branch} to pilot/fixture/ and closes open pilot/* PRs.")
    if not yes:
        try:
            ans = input("Type y to continue: ").strip().lower()
        except EOFError:
            ans = ""
        if ans != "y":
            print("declined")
            return 5
    for pr in open_pilot_prs(cfg.repo):
        gh("pr", "close", str(pr["number"]), "-R", cfg.repo, "--delete-branch",
           "--comment", "Closed by `pilot reset-fixture`.")
        print(f"closed PR #{pr['number']} ({pr['headRefName']})")
    with tempfile.TemporaryDirectory(prefix="pilot-reset-") as t:
        shutil.copytree(paths.FIXTURE_TEMPLATE, t, dirs_exist_ok=True)
        git("init", "--quiet", "-b", cfg.branch, cwd=t)
        git("add", "-A", cwd=t)
        git("commit", "--quiet", "-m", "pilot: reset fixture", cwd=t)
        git("push", "--quiet", "--force", url(cfg.repo), f"HEAD:refs/heads/{cfg.branch}", cwd=t)
        base = git("rev-parse", "HEAD", cwd=t).stdout.strip()
    # remove stale pilot/* branches without open PRs
    r = git("ls-remote", "--heads", url(cfg.repo), "refs/heads/pilot/*", check=False)
    for line in r.stdout.splitlines():
        ref = line.split()[-1]
        git("push", "--quiet", url(cfg.repo), f":{ref}", check=False)
    paths.BUILD.mkdir(parents=True, exist_ok=True)
    paths.FIXTURE_BASE.write_text(base + "\n")
    print(f"fixture reset: {cfg.repo}@{cfg.branch} = {base}")
    return 0
