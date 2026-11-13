"""Builds a synthetic evidence directory for a correct pilot run (T049) and mutations of it."""
import hashlib
import json
from pathlib import Path

from specfoundry_pilot import prompt

FIX = Path(__file__).resolve().parents[1] / "fixture" / "specs" / "001-slugify"


def _jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def build(d: Path) -> Path:
    spec, tasks, plan = (FIX / "spec.md").read_text(), (FIX / "tasks.md").read_text(), (FIX / "plan.md").read_text()
    full, _ = prompt.build_prompt(spec, tasks, plan, None)
    induced, rec = prompt.build_prompt(spec, tasks, plan, prompt.INDUCTION)
    ev = []

    def e(stage, task, attempt, event, detail=""):
        ev.append({"seq": len(ev) + 1, "at": "2026-11-13T00:00:00Z", "stage": stage, "task": task,
                   "attempt": attempt, "event": event, "detail": detail})
    e("run", None, None, "run_started")
    e("gate", "A", None, "gate_allow"); e("gate", "B", None, "gate_refuse")
    e("mode", None, None, "mode_confirmed", "{}")
    e("attempt", "A", 1, "attempt_created"); e("attempt", "A", 1, "attempt_collected")
    e("grade", "A", 1, "grade_fail", "G5_hidden_tests"); e("gate", "B", None, "gate_refuse")
    e("retry", "A", 2, "retry_confirmed")
    e("attempt", "A", 2, "attempt_created"); e("attempt", "A", 2, "attempt_collected")
    e("grade", "A", 2, "grade_pass"); e("publish", "A", 2, "pr_opened", "u1")
    e("gate", "B", None, "gate_refuse"); e("run", None, None, "run_paused(awaiting-merge)")
    e("reconcile", "A", 2, "reconcile_applied"); e("status", "A", None, "task_verified")
    e("gate", "B", None, "gate_allow")
    e("attempt", "B", 1, "attempt_created"); e("attempt", "B", 1, "attempt_collected")
    e("grade", "B", 1, "grade_pass"); e("publish", "B", 1, "pr_opened", "u2")
    _jsonl(d / "events.jsonl", ev)
    state = {"run_id": d.name, "state": "succeeded", "mode": {"spend_cap_usd": 1.0, "token_cap": 2000000},
             "tasks": {"A": {"attempts": [{"n": 1}, {"n": 2}]}, "B": {"attempts": [{"n": 1}]}}}
    (d / "run.json").write_text(json.dumps(state))
    for task, n, p, ind in (("A", 1, induced, rec), ("A", 2, full, None), ("B", 1, full, None)):
        a = d / "attempts" / f"{task}-{n}"
        a.mkdir(parents=True, exist_ok=True)
        (a / "prompt.md").write_text(p)
        if ind:
            (a / "induction.json").write_text(json.dumps(ind))
        (a / "report.json").write_text(json.dumps({"spend": {"cap_usd": 1.0, "token_cap": 2000000, "cap_mode": "token-fallback",
                                                             "cost_usd": 0.0, "tokens": 180000, "stopped_by_cap": False},
                                                   "harness": {"exit": 0}}))
    (d / "prs.json").write_text(json.dumps([
        {"task": "A", "number": 1, "url": "u1", "draft": True, "author": "bot", "publisher_identity": "bot"},
        {"task": "B", "number": 2, "url": "u2", "draft": True, "author": "bot", "publisher_identity": "bot"}]))
    rows = [{"id": f"GM0{i}", "requirement": "FR-002", "result": "pass", "description": "", "detail": ""} for i in range(1, 5)]
    rows += [{"id": pid, "requirement": "FR-007", "result": "pass", "description": "", "detail": f"{t}"}
             for pid in ("P04", "P09") for t in ("A-1", "A-2", "B-1")]
    _jsonl(d / "checks" / "results.jsonl", rows)
    _jsonl(d / "teardown.jsonl", [{"id": f"T0{i}", "requirement": "N3", "result": "pass", "description": "", "detail": ""}
                                  for i in (1, 2, 3)])
    return d


def sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()
