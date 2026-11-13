"""Grade one attempt in a fresh grader namespace (FR-010-FR-012, R7)."""
from __future__ import annotations

import json

from . import evidence, frame, k8s, paths, worker

TIMEOUT = 300


def _fail(run, task, n, imgs, failure):
    return {"version": 1, "run_id": run.id, "task": task, "attempt": n, "result": "fail", "failure": failure,
            "grader_image": imgs["tools"],
            "checks": [{"id": c, "result": "skipped", "detail": failure} for c in
                       ("G1_bundle_applies", "G2_allowed_paths", "G3_tasks_checked", "G4_visible_tests", "G5_hidden_tests")]}


def grade(run, imgs: dict, runner, task: str, n: int) -> dict:
    ns = f"pilot-g-{task.lower()}-{n}"
    adir = run.attempt_dir(task, n)
    item = paths.TASKS[task]
    run.event("grade", task, n, "grade_started", ns)
    k8s.delete_ns(ns)
    handle = None
    try:
        k8s.apply(k8s.render(paths.MANIFESTS / "grader.yaml.tmpl", NS=ns, RUN_ID=run.id))
        sub = {"base.bundle": worker.base_bundle(run, task, n), "meta.json": adir / "meta.json"}
        if (adir / "change.bundle").exists():
            sub["change.bundle"] = adir / "change.bundle"
        k8s.create_configmap(ns, "submission", sub)
        k8s.create_configmap(ns, "grading", {f"test_hidden_{item}.py": paths.GRADING / f"test_hidden_{item}.py"})
        job = k8s.render(paths.MANIFESTS / "grader-job.yaml.tmpl", NS=ns, TOOLS_IMAGE=imgs["tools"])
        handle = runner.submit("grader", ns, "grader", job)
        outcome = runner.wait(handle, TIMEOUT + 60)
        if outcome in ("DeadlineExceeded", "Timeout"):
            report = _fail(run, task, n, imgs, "grader_timeout")
        else:
            files, err = frame.decode(runner.collect(handle), required=("grade.json",))
            if err:
                report = _fail(run, task, n, imgs, "no_result" if err == "no_result" else "bad_frame")
            else:
                report = json.loads(files["grade.json"])
                if report.get("result") not in ("pass", "fail") or report.get("attempt") != n or report.get("task") != task:
                    report = _fail(run, task, n, imgs, "bad_frame")
    except Exception as e:  # noqa: BLE001 - grader trouble is never a pass
        report = _fail(run, task, n, imgs, "grader_error")
        run.event("grade", task, n, "grade_error", f"{e.__class__.__name__}: {str(e)[:300]}")
    finally:
        if handle:
            runner.delete(handle)
        else:
            k8s.delete_ns(ns)
    evidence.write_json(adir / "grade.json", report)
    failed = [c["id"] for c in report["checks"] if c["result"] == "fail"]
    run.event("grade", task, n, f"grade_{report['result']}", report.get("failure") or ",".join(failed))
    return report
