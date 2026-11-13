"""Reconcile after a human merge: check reality, propose `planned -> verified`, ask, apply.

Deterministic pilot equivalent of the spec-status `reconcile` skill (research R9). The
status edit is pushed with the operator's own git credentials (a human action under
constitution V), never with a worker, grader or publisher credential.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import evidence, fixture, paths

ROADMAP_REL = ".specify/memory/roadmap.md"


def status_edit(roadmap_text: str, item_id: str) -> str:
    pat = re.compile(rf"^(### {re.escape(item_id)} — .*?\[status: )planned(\])[ \t]*$", re.M)
    hits = pat.findall(roadmap_text)
    if len(hits) != 1:
        raise ValueError(f"expected exactly one planned heading for {item_id}, found {len(hits)}")
    return pat.sub(lambda m: f"{m.group(1)}verified{m.group(2)}", roadmap_text, count=1)


@dataclass
class Reconciler:
    pr_view: Callable[[int], dict]
    tasks_percent: Callable[[str], int | None]
    default_file: Callable[[str], bytes | None]
    graded_file: Callable[[str], bytes | None]
    roadmap_text: Callable[[], str]
    push: Callable[[str], str]
    ask: Callable[[str], str]

    def run(self, task: str, item_id: str, pr_number: int, changed_paths: list[str]) -> tuple[int, dict]:
        rec = {"task": task, "item_id": item_id, "pr": pr_number, "pr_merged": False, "merge_commit": None,
               "tasks_percent": None, "tree_matches_graded": None, "mismatched_paths": [],
               "proposed": None, "approved": False, "applied_commit": None, "reason": None, "at": evidence.now()}
        pr = self.pr_view(pr_number)
        rec["pr_merged"] = bool(pr.get("state") == "MERGED" and pr.get("mergedAt"))
        rec["merge_commit"] = (pr.get("mergeCommit") or {}).get("oid")
        if not rec["pr_merged"]:
            rec["reason"] = "NOT_MERGED"
            return 4, rec
        rec["tasks_percent"] = self.tasks_percent(item_id)
        if rec["tasks_percent"] != 100:
            rec["reason"] = "TASKS_INCOMPLETE"
            return 1, rec
        mism = [p for p in changed_paths if self.default_file(p) != self.graded_file(p)]
        rec["tree_matches_graded"] = not mism
        rec["mismatched_paths"] = mism
        if mism:
            rec["reason"] = "TREE_MISMATCH"
            return 1, rec
        old = self.roadmap_text()
        new = status_edit(old, item_id)
        diff = [f"- {a}\n+ {b}" for a, b in zip(old.splitlines(), new.splitlines()) if a != b]
        rec["proposed"] = "planned→verified"
        print(f"Reconcile proposal for task {task} (item {item_id}), PR #{pr_number} merged "
              f"({rec['merge_commit']}), tasks 100%, graded tree matches:\n" + "\n".join(diff))
        ans = (self.ask(f"Apply '{item_id}: planned → verified' to the fixture roadmap? [y/N] ") or "").strip().lower()
        if ans != "y":
            rec["reason"] = "DECLINED"
            return 5, rec
        rec["approved"] = True
        rec["applied_commit"] = self.push(new)
        return 0, rec


def ask_tty(question: str) -> str:
    """Ask on the controlling terminal. No terminal (or any error) -> "" (decline, fail closed).

    A tty is not seekable, so it must be opened separately for writing and reading
    (text mode "r+" raises io.UnsupportedOperation).
    """
    try:
        with open("/dev/tty", "w") as out, open("/dev/tty", "r") as inp:
            out.write(question)
            out.flush()
            return inp.readline()
    except (OSError, ValueError):
        return ""


def for_fixture(cfg, run, task: str, attempt_dir: Path, base_rev: str, ask=ask_tty) -> tuple[Reconciler, Callable[[], None]]:
    """Build a Reconciler bound to a fresh full clone of the fixture default branch."""
    clone, _ = fixture.fresh_clone(cfg.repo, cfg.branch, depth=None)
    graded = Path(run.dir / f".graded-{task}")
    shutil.rmtree(graded, ignore_errors=True)
    base = base_rev
    subprocess.run(["git", "clone", "--quiet", str(clone), str(graded)], check=True)
    subprocess.run(["git", "-C", str(graded), "checkout", "--quiet", base], check=True)
    subprocess.run(["git", "-C", str(graded), "fetch", "--quiet", str(attempt_dir / "change.bundle"),
                    "HEAD:refs/pilot/graded"], check=True)
    subprocess.run(["git", "-C", str(graded), "checkout", "--quiet", "refs/pilot/graded"], check=True)

    def read(root: Path, p: str):
        f = root / p
        return f.read_bytes() if f.is_file() else None

    def tasks_percent(item_id):
        r = subprocess.run(["spec", "status", "--json", "--root", str(clone)], capture_output=True, text=True)
        doc = json.loads(r.stdout)
        it = next(i for i in doc["items"] if i["id"] == item_id)
        return (it.get("tasks") or {}).get("percent")

    def pr_view(n):
        out = fixture.gh("pr", "view", str(n), "-R", cfg.repo, "--json", "state,mergedAt,mergeCommit").stdout
        return json.loads(out)

    def push(text):
        (clone / ROADMAP_REL).write_text(text)
        fixture.git("add", ROADMAP_REL, cwd=clone)
        fixture.git("commit", "--quiet", "-m", f"pilot: {paths.TASKS[task]} verified (run {run.id})", cwd=clone)
        fixture.git("push", "--quiet", fixture.url(cfg.repo), f"HEAD:refs/heads/{cfg.branch}", cwd=clone)
        return fixture.git("rev-parse", "HEAD", cwd=clone).stdout.strip()

    r = Reconciler(pr_view=pr_view, tasks_percent=tasks_percent, default_file=lambda p: read(clone, p),
                   graded_file=lambda p: read(graded, p), roadmap_text=lambda: (clone / ROADMAP_REL).read_text(),
                   push=push, ask=ask)

    def cleanup():
        shutil.rmtree(clone, ignore_errors=True)
        shutil.rmtree(graded, ignore_errors=True)

    return r, cleanup
