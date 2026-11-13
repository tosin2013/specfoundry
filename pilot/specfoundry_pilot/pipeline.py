"""`pilot run` / `pilot resume`: one governed cycle for fixture tasks A then B.

Every human decision point fails closed: no TTY or anything but `y` means "no".
  mode confirmation (FR-023)        -> exit 5, no worker staged
  retry confirmation (FR-017)       -> paused(awaiting-retry), exit 6
  merge of A's PR (FR-018a)          -> paused(awaiting-merge), exit 0 / resume exit 4
  reconcile approval (FR-018)        -> exit 5, roadmap unchanged
"""
from __future__ import annotations

import datetime as _dt
import json
import shutil
import subprocess

from . import evidence, fixture, gate, grader, images, paths, publisher, reconcile, worker
from .runner.jobs import JobsRunner

try:
    from . import checks  # US3 live checks
except ImportError:  # pragma: no cover
    checks = None

EXIT_OK, EXIT_FAIL, EXIT_ERROR, EXIT_AWAIT_MERGE, EXIT_DECLINED, EXIT_AWAIT_RETRY = 0, 1, 2, 4, 5, 6


def ask(question: str) -> bool:
    return reconcile.ask_tty(question).strip().lower() == "y"


def mode_of(cfg) -> dict:
    return {"name": "step-by-step", "retry_limit": cfg.retry_limit, "spend_cap_usd": float(cfg["PILOT_SPEND_CAP_USD"]),
            "token_cap": int(cfg["PILOT_TOKEN_CAP"]), "worker_deadline_s": worker.DEADLINE}


def confirm_mode(run, cfg, ask_fn=ask) -> bool:
    mode = mode_of(cfg)
    print(f"Run mode for this pilot: {json.dumps(mode, sort_keys=True)}\n"
          "  one attempt at a time; every retry needs your confirmation; risk rating is out of scope in M1.")
    if not ask_fn("Confirm this mode and start staging workers? [y/N] "):
        run.event("mode", None, None, "mode_declined", json.dumps(mode, sort_keys=True))
        return False
    run.state["mode"] = mode
    run.event("mode", None, None, "mode_confirmed", json.dumps(mode, sort_keys=True))
    return True


def confirm_retry(run, task: str, n: int, total: int, ask_fn=ask) -> bool:
    ok = ask_fn(f"Retry {task} (attempt {n} of {total})? [y/N] ")
    run.event("retry", task, n, "retry_confirmed" if ok else "retry_declined", "")
    return ok


def gate_task(run, cfg, task: str) -> dict:
    seq = run.next_gate_seq()
    d = gate.evaluate_fresh(cfg, task, seq=seq, out_dir=run.dir / "gate")
    t = run.task(task)
    t.setdefault("gate_seqs", []).append(seq)
    if d["decision"] == "allow":
        t["base_revision"] = d["input"]["fixture_commit"]
    run.save()
    run.event("gate", task, None, f"gate_{d['decision']}", f"seq={seq} " + ",".join(d["reasons"]))
    print(f"  gate {task}: {d['decision']} {d['reasons']}")
    return d


def _clone_at(cfg, rev: str):
    path, _ = fixture.fresh_clone(cfg.repo, cfg.branch, depth=None)
    subprocess.run(["git", "-C", str(path), "checkout", "--quiet", rev], check=True)
    return path


def _pause(run, state: str, **pending) -> None:
    run.state["pending"] = pending
    run.state["paused_at"] = evidence.now()
    run.set_run_state(f"paused({state})")
    evidence.write_summary(run)


def _fail(run, reason: str) -> int:
    run.set_run_state("failed", reason)
    evidence.write_summary(run)
    print(f"run {run.id} FAILED: {reason}")
    return EXIT_FAIL


def run_task(run, cfg, imgs, runner, task: str, start_n: int = 1) -> int:
    """Attempts (confirmed retries), grading, publishing, then the post-publish step."""
    t = run.task(task)
    total = 1 + cfg.retry_limit
    n = start_n
    while True:
        t["state"] = "attempting"
        run.save()
        clone = _clone_at(cfg, t["base_revision"])
        try:
            att = worker.run_attempt(run, cfg, imgs, runner, task, n, clone, t["base_revision"], checks=checks)
        finally:
            shutil.rmtree(clone, ignore_errors=True)
        if att["state"] == "collected":
            g = grader.grade(run, imgs, runner, task, n)
            att["result"] = g["result"]
            att["state"] = "passed" if g["result"] == "pass" else "failed"
            if g["result"] != "pass":
                att["reason"] = g.get("failure") or "grade_fail"
        else:
            att["result"] = "fail"
        t["attempts"] = [a for a in t.get("attempts", []) if a["n"] != n] + [att]
        run.save()
        if att["state"] == "passed":
            t["passing_attempt"] = n
            break
        if task == "A":
            d = gate_task(run, cfg, "B")
            if d["decision"] != "refuse":
                return _fail(run, "B_NOT_BLOCKED")
        if n >= total:
            return _fail(run, f"{task}_RETRIES_EXHAUSTED")
        if not confirm_retry(run, task, n + 1, total):
            _pause(run, "awaiting-retry", task=task, n=n + 1)
            print(f"paused: retry of {task} not confirmed. `pilot resume` asks again.")
            return EXIT_AWAIT_RETRY
        n += 1
    return publish_task(run, cfg, imgs, runner, task)


def publish_task(run, cfg, imgs, runner, task: str) -> int:
    t = run.task(task)
    n = t["passing_attempt"]
    t["state"] = "publishing"
    run.save()
    try:
        pr = publisher.publish(run, cfg, imgs, runner, task, n)
    except Exception as e:  # noqa: BLE001 - publisher trouble is resumable, never "verified"
        t["state"] = "publish-failed"
        run.event("publish", task, n, "publish_failed", f"{e.__class__.__name__}: {str(e)[:300]}")
        _pause(run, "awaiting-publish", task=task, n=n)
        print(f"publisher failed for {task}: {e}\n`pilot resume` re-runs it (idempotent).")
        return EXIT_FAIL
    t["state"] = "published"
    t["pr"] = pr
    run.save()
    if checks:
        checks.run_cluster_checks(run, imgs)
    if task == "A":
        d = gate_task(run, cfg, "B")
        if d["decision"] != "refuse":
            return _fail(run, "B_NOT_BLOCKED")
        t["state"] = "awaiting-merge"
        _pause(run, "awaiting-merge", task="A")
        print(f"\nTask A draft PR: {pr['url']}\nReview and merge it on GitHub yourself, then run: pilot/pilot resume")
        return EXIT_OK
    return finish(run)


def finish(run) -> int:
    from . import audit
    ok = audit.run(run)
    if not ok:
        return _fail(run, "AUDIT")
    run.set_run_state("succeeded")
    evidence.write_summary(run)
    print(f"run {run.id} succeeded. Evidence: {run.dir.relative_to(paths.ROOT)}")
    return EXIT_OK


def run(cfg) -> int:
    imgs = images.load()
    runner = JobsRunner()
    open_prs = fixture.open_pilot_prs(cfg.repo)
    if open_prs:
        print(f"open pilot PRs exist on {cfg.repo}: {[p['url'] for p in open_prs]}\nrun `pilot reset-fixture` first")
        return EXIT_ERROR
    if not paths.FIXTURE_BASE.exists():
        print("no fixture base recorded; run `pilot reset-fixture` first")
        return EXIT_ERROR
    r = evidence.new_run()
    print(f"== run {r.id}")
    r.state["fixture_base"] = paths.FIXTURE_BASE.read_text().strip()
    paths.MODEL_HOST.write_text(cfg.model_hosts[0] + "\n")  # for the P06 probe; never in evidence
    evidence.write_config_json(r, cfg)
    evidence.write_versions(r, imgs)
    r.event("run", None, None, "run_started", cfg.repo)
    if checks:
        checks.gate_matrix(r)
        if any(row["result"] != "pass" for row in evidence.read_jsonl(r.dir / "checks/results.jsonl")
               if row["id"].startswith("GM")):
            return _fail(r, "GATE_MATRIX")
    if gate_task(r, cfg, "A")["decision"] != "allow":
        return _fail(r, "A_REFUSED")
    if gate_task(r, cfg, "B")["decision"] != "refuse":
        return _fail(r, "B_NOT_BLOCKED")
    if not confirm_mode(r, cfg):
        r.set_run_state("failed", "MODE_NOT_CONFIRMED")
        evidence.write_summary(r)
        return EXIT_DECLINED
    r.save()
    return run_task(r, cfg, imgs, runner, "A")


def resume(cfg, run_id: str | None) -> int:
    r = evidence.load_run(run_id)
    if r is None or not str(r.state.get("state", "")).startswith("paused"):
        print(f"no paused run{' ' + run_id if run_id else ''} (state={r.state.get('state') if r else None})")
        return EXIT_ERROR
    imgs = images.load()
    runner = JobsRunner()
    st, pend = r.state["state"], r.state.get("pending") or {}
    r.state["state"] = "in-progress"
    r.save()
    r.event("run", None, None, "run_resumed", st)
    if st == "paused(awaiting-retry)":
        task, n = pend["task"], int(pend["n"])
        if not confirm_retry(r, task, n, 1 + cfg.retry_limit):
            _pause(r, "awaiting-retry", task=task, n=n)
            return EXIT_AWAIT_RETRY
        return run_task(r, cfg, imgs, runner, task, start_n=n)
    if st == "paused(awaiting-publish)":
        return publish_task(r, cfg, imgs, runner, pend["task"])
    if st != "paused(awaiting-merge)":
        print(f"cannot resume from {st}")
        return EXIT_ERROR
    # Human merge happened (or not): reconcile A.
    paused_at = _dt.datetime.strptime(r.state.get("paused_at", evidence.now()), "%Y-%m-%dT%H:%M:%SZ")
    tA = r.task("A")
    n = tA["passing_attempt"]
    rec_obj, cleanup = reconcile.for_fixture(cfg, r, "A", r.attempt_dir("A", n), tA["base_revision"])
    try:
        code, rec = rec_obj.run("A", paths.TASKS["A"], tA["pr"]["number"],
                                next(a for a in tA["attempts"] if a["n"] == n).get("changed_paths") or [])
    finally:
        cleanup()
    evidence.write_json(r.dir / "reconcile" / "A.json", rec)
    r.event("reconcile", "A", n, f"reconcile_{rec.get('reason') or 'applied'}", rec.get("applied_commit") or "")
    if code == EXIT_AWAIT_MERGE:
        _pause(r, "awaiting-merge", task="A")
        print("A's PR is not merged yet. Merge it on GitHub, then run `pilot resume` again.")
        return EXIT_AWAIT_MERGE
    if code == EXIT_DECLINED:
        _pause(r, "awaiting-merge", task="A")
        print("status change declined; roadmap unchanged; B stays blocked.")
        return EXIT_DECLINED
    if code != 0:
        return _fail(r, f"RECONCILE_{rec.get('reason')}")
    wait = int((_dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) - paused_at).total_seconds())
    r.event("reconcile", "A", None, "merge_wait_seconds", str(wait))
    tA["state"] = "verified"
    r.save()
    r.event("status", "A", None, "task_verified", rec.get("applied_commit") or "")
    if gate_task(r, cfg, "B")["decision"] != "allow":
        return _fail(r, "B_STILL_BLOCKED")
    return run_task(r, cfg, imgs, runner, "B")
