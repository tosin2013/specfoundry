"""Grader (runs in a fresh `pilot-g-<task>-<n>` namespace with no secrets and no egress; R7).

Inputs  /in/meta.json {run_id, task, attempt, item_id, base_revision, allowed_paths}
        /in/base.bundle, /in/change.bundle (may be absent)
        /grading/test_hidden_<item_id>.py  (grading material: never mounted in a worker)
Output  stdout frame with grade.json (contracts/grade-report.schema.json)
"""
from __future__ import annotations

import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile

CHECKS = ["G1_bundle_applies", "G2_allowed_paths", "G3_tasks_checked", "G4_visible_tests", "G5_hidden_tests"]


def run(cmd, cwd=None, env=None, timeout=180):
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)[-3000:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def grade(meta: dict, inp: str = "/in", grading: str = "/grading", work: str | None = None) -> dict:
    work = work or tempfile.mkdtemp(prefix="grade-")
    repo = os.path.join(work, "repo")
    results = []

    def add(cid, ok, detail=""):
        results.append({"id": cid, "result": "pass" if ok else "fail", "detail": str(detail)[-4000:]})
        return ok

    base = meta["base_revision"]
    change = os.path.join(inp, "change.bundle")
    ok = os.path.exists(change)
    detail = "no change.bundle from worker"
    if ok:
        rc1, o1 = run(["git", "clone", "--quiet", os.path.join(inp, "base.bundle"), repo])
        rc2, o2 = (run(["git", "checkout", "--quiet", base], cwd=repo) if rc1 == 0 else (1, ""))
        rc3, o3 = (run(["git", "bundle", "verify", change], cwd=repo) if rc2 == 0 else (1, ""))
        rc4, o4 = (run(["git", "fetch", "--quiet", change, "HEAD:refs/pilot/graded"], cwd=repo) if rc3 == 0 else (1, ""))
        rc5, o5 = (run(["git", "merge-base", "--is-ancestor", base, "refs/pilot/graded"], cwd=repo) if rc4 == 0 else (1, ""))
        rc6, o6 = (run(["git", "checkout", "--quiet", "refs/pilot/graded"], cwd=repo) if rc5 == 0 else (1, ""))
        ok = rc6 == 0
        detail = " | ".join(x for x in (o1, o2, o3, o4, o5, o6) if x)[:2000] or "fast-forward from base"
    if add("G1_bundle_applies", ok, detail):
        rc, out = run(["git", "diff", "--name-only", base, "HEAD"], cwd=repo)
        changed = [p for p in out.splitlines() if p]
        bad = [p for p in changed if not any(fnmatch.fnmatch(p, g) for g in meta["allowed_paths"])]
        if add("G2_allowed_paths", rc == 0 and not bad and bool(changed), f"changed={changed} disallowed={bad}"):
            rc, out = run(["spec", "status", "--json", "--root", repo])
            pct = None
            try:
                item = next(i for i in json.loads(out if rc in (0, 1) else "{}")["items"] if i["id"] == meta["item_id"])
                pct = (item.get("tasks") or {}).get("percent")
            except Exception:  # noqa: BLE001
                pass
            if add("G3_tasks_checked", pct == 100, f"tasks percent={pct}"):
                env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
                rc, out = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/"], cwd=repo, env=env)
                if add("G4_visible_tests", rc == 0, out):
                    hidden = os.path.join(grading, f"test_hidden_{meta['item_id']}.py")
                    tdir = os.path.join(work, "hidden")
                    os.makedirs(tdir, exist_ok=True)
                    shutil.copy(hidden, tdir)
                    env["PYTHONPATH"] = os.path.join(repo, "src")
                    rc, out = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                   os.path.join(tdir, os.path.basename(hidden))], cwd=tdir, env=env)
                    add("G5_hidden_tests", rc == 0, out)
    done = {r["id"] for r in results}
    for cid in CHECKS:
        if cid not in done:
            results.append({"id": cid, "result": "skipped", "detail": "earlier check failed"})
    passed = all(r["result"] == "pass" for r in results) and len(results) == 5
    return {"version": 1, "run_id": meta["run_id"], "task": meta["task"], "attempt": int(meta["attempt"]),
            "result": "pass" if passed else "fail", "failure": None,
            "grader_image": os.environ.get("GRADER_IMAGE", "unknown"), "checks": results}


def main() -> int:
    sys.path.insert(0, "/usr/local/lib/pilot")
    import frame  # noqa: E402
    meta = json.load(open("/in/meta.json"))
    try:
        report = grade(meta)
    except Exception as e:  # noqa: BLE001 - any grader crash is a fail
        report = {"version": 1, "run_id": meta.get("run_id"), "task": meta.get("task"),
                  "attempt": int(meta.get("attempt", 1)), "result": "fail", "failure": "grader_error",
                  "grader_image": os.environ.get("GRADER_IMAGE", "unknown"),
                  "checks": [{"id": c, "result": "skipped", "detail": f"grader crashed: {e}"[:400]} for c in CHECKS]}
    out = os.path.join(tempfile.mkdtemp(), "grade.json")
    with open(out, "w") as f:
        json.dump(report, f)
    frame.main(["emit", f"grade.json={out}"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
