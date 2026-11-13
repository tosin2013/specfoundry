"""Fail-closed gate over `spec status --json` (research R3, contracts/gate-decision.schema.json).

allow  <=>  every rule passes; anything else (including any exception) refuses.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from . import evidence

STARTABLE = ("planned", "specced", "in-progress")


def decide(item_id: str, exit_code, stdout: str) -> tuple[str, list[str]]:
    """Pure decision from the status tool's exit code and stdout. Never raises."""
    try:
        return _decide(item_id, exit_code, stdout)
    except Exception:  # noqa: BLE001 - fail closed on anything unexpected
        return "refuse", ["UNEVALUABLE:internal"]


def _decide(item_id, exit_code, stdout):
    # Rule 1: exit code 0 or 1 only (2 = unevaluable).
    if exit_code is None:
        return "refuse", ["UNEVALUABLE:spawn_failed"]
    if exit_code not in (0, 1):
        return "refuse", [f"UNEVALUABLE:exit_{int(exit_code)}"]
    if not stdout or not stdout.strip():
        return "refuse", ["UNEVALUABLE:empty"]
    # Rule 2: parseable, schema 1.0, complete, no error.
    try:
        doc = json.loads(stdout)
    except ValueError:
        return "refuse", ["UNEVALUABLE:bad_json"]
    if not isinstance(doc, dict) or doc.get("schema_version") != "1.0":
        return "refuse", ["SCHEMA_MISMATCH"]
    if doc.get("error") is not None:
        return "refuse", ["UNEVALUABLE:tool_error"]
    if doc.get("complete") is not True:
        return "refuse", ["INCOMPLETE"]
    items = doc.get("items")
    if not isinstance(items, list):
        return "refuse", ["SCHEMA_MISMATCH"]
    # Rule 3: exactly one item, status known, active.
    matches = [i for i in items if isinstance(i, dict) and i.get("id") == item_id]
    if not matches:
        return "refuse", ["ITEM_MISSING"]
    if len(matches) > 1:
        return "refuse", ["ITEM_DUPLICATE"]
    item = matches[0]
    reasons = []
    if item.get("status_known") is not True:
        reasons.append("STATUS_UNKNOWN")
    if item.get("active") is not True:
        reasons.append("INACTIVE")
    # Rule 4: startable status.
    status = item.get("status")
    if status == "implemented":
        reasons.append("ALREADY_IMPLEMENTED")
    elif status == "verified":
        reasons.append("ALREADY_VERIFIED")
    elif status not in STARTABLE:
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in str(status).lower()) or "none"
        reasons.append(f"STATUS_NOT_STARTABLE:{slug}")
    # Rule 5: every dependency satisfied (missing/non-true counts as unsatisfied).
    deps = item.get("dependencies")
    if not isinstance(deps, list):
        return "refuse", ["SCHEMA_MISMATCH"]
    unsatisfied = [d for d in deps if not (isinstance(d, dict) and d.get("satisfied") is True)]
    for d in unsatisfied:
        did = str(d.get("id", "unknown")) if isinstance(d, dict) else "unknown"
        reasons.append(f"DEP_UNSATISFIED:{did}")
    # Rule 6: no error diagnostics for this item.
    for diag in doc.get("diagnostics") or []:
        if isinstance(diag, dict) and diag.get("item_id") == item_id and diag.get("severity") == "error":
            reasons.append(f"ITEM_ERROR_DIAGNOSTIC:{diag.get('code', 'UNKNOWN')}")
    # Rule 7: global blocked_count must agree with the per-item view.
    blocked = (doc.get("summary") or {}).get("blocked_count")
    if unsatisfied and not (isinstance(blocked, int) and blocked >= 1):
        reasons.append("INCONSISTENT_BLOCKED_COUNT")
    return ("refuse", reasons) if reasons else ("allow", ["OK"])


def spec_version(spec_bin: str) -> str:
    try:
        r = subprocess.run([spec_bin, "--version"], capture_output=True, text=True, timeout=20)
        return (r.stdout.splitlines() or ["unknown"])[0].strip()
    except Exception:  # noqa: BLE001
        return "unavailable"


def evaluate(task: str, item_id: str, root, seq: int, out_dir: Path | None = None,
             repo: str = "local", commit: str | None = None, spec_bin: str | None = None) -> dict:
    spec_bin = spec_bin or os.environ.get("SPEC_BIN", "spec")
    exit_code, stdout = None, ""
    try:
        r = subprocess.run([spec_bin, "status", "--json", "--root", str(root)],
                           capture_output=True, text=True, timeout=60)
        exit_code, stdout = r.returncode, r.stdout
    except Exception:  # noqa: BLE001 - spawn failure / timeout -> unevaluable
        exit_code = None
    decision, reasons = decide(item_id, exit_code, stdout)
    sha = hashlib.sha256(stdout.encode()).hexdigest() if stdout else None
    d = {
        "version": 1, "seq": max(int(seq), 1), "task": task, "item_id": item_id,
        "decision": decision, "reasons": reasons,
        "input": {"fixture_repo": repo, "fixture_commit": commit, "spec_version": spec_version(spec_bin),
                  "spec_status_exit": exit_code, "spec_status_json_sha256": sha},
        "at": evidence.now(),
    }
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{d['seq']}-{task}.status.json").write_text(stdout)
        evidence.write_json(out_dir / f"{d['seq']}-{task}.json", d)
    return d


def evaluate_fresh(cfg, task: str, seq: int, out_dir: Path | None = None) -> dict:
    """Gate against a fresh clone of the fixture's default branch (FR-019)."""
    from . import fixture, paths
    item = paths.TASKS[task]
    try:
        clone, commit = fixture.fresh_clone(cfg.repo, cfg.branch)
    except Exception:  # noqa: BLE001
        d = {"version": 1, "seq": max(int(seq), 1), "task": task, "item_id": item, "decision": "refuse",
             "reasons": ["UNEVALUABLE:clone_failed"],
             "input": {"fixture_repo": cfg.repo, "fixture_commit": None, "spec_version": spec_version("spec"),
                       "spec_status_exit": None, "spec_status_json_sha256": None},
             "at": evidence.now()}
        if out_dir is not None:
            evidence.write_json(Path(out_dir) / f"{d['seq']}-{task}.json", d)
        return d
    try:
        return evaluate(task, item, clone, seq, out_dir, repo=cfg.repo, commit=commit)
    finally:
        import shutil
        shutil.rmtree(clone, ignore_errors=True)
