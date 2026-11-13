"""One worker attempt: isolated namespace, inputs, Job, frame collection (FR-005-FR-009c)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import evidence, frame, k8s, paths, prompt
from .prompt import INDUCTION, build_prompt  # noqa: F401  (re-export, T024)

DEADLINE = 1200


def allowed_paths(task: str) -> list[str]:
    return ["src/slugkit/*", "tests/*", f"{paths.SPEC_DIRS[task]}/tasks.md"]


def ns_for(task: str, n: int) -> str:
    return f"pilot-w-{task.lower()}-{n}"


def make_inputs(run, task: str, n: int, clone: Path, base_rev: str) -> tuple[Path, dict | None]:
    """Write worker inputs to pilot/.build (base bundle) and copies to evidence (prompt, meta)."""
    adir = run.attempt_dir(task, n)
    idir = paths.BUILD / "inputs" / run.id / f"{task}-{n}"
    idir.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != base_rev:
        raise RuntimeError(f"clone HEAD {head} != base {base_rev}")
    subprocess.run(["git", "-C", str(clone), "bundle", "create", "-q", str(idir / "base.bundle"), "HEAD"], check=True)
    sd = clone / paths.SPEC_DIRS[task]
    induction = INDUCTION if (task == "A" and n == 1) else None
    text, record = prompt.build_prompt((sd / "spec.md").read_text(), (sd / "tasks.md").read_text(),
                                       (sd / "plan.md").read_text(), induction, f"{paths.SPEC_DIRS[task]}/tasks.md")
    meta = {"run_id": run.id, "task": task, "attempt": n, "item_id": paths.TASKS[task], "base_revision": base_rev,
            "allowed_paths": allowed_paths(task),
            "induction": ({"name": record["name"], "heading": record["removed_heading"],
                           "spec_path": f"{paths.SPEC_DIRS[task]}/spec.md"} if record else None)}
    if record:
        record["workspace_spec_trimmed"] = f"{paths.SPEC_DIRS[task]}/spec.md"
    for d in (idir, adir):
        (d / "prompt.md").write_text(text)
        evidence.write_json(d / "meta.json", meta)
    if record:
        evidence.write_json(adir / "induction.json", record)
    return idir, record


def proxy_denials(since: str) -> str:
    r = k8s.kubectl("-n", "pilot-egress-model", "logs", "deploy/proxy", f"--since-time={since}", check=False, timeout=60)
    return "\n".join(l for l in r.stdout.splitlines() if "refused" in l.lower()) + "\n"


def run_attempt(run, cfg, imgs: dict, runner, task: str, n: int, clone: Path, base_rev: str, checks=None) -> dict:
    ns = ns_for(task, n)
    adir = run.attempt_dir(task, n)
    idir, induction = make_inputs(run, task, n, clone, base_rev)
    att = {"n": n, "namespace": ns, "induction": induction["name"] if induction else None,
           "image": imgs["worker"], "base_revision": base_rev, "state": "created", "reason": None}
    run.event("attempt", task, n, "attempt_created", f"ns={ns} induction={att['induction']}")
    k8s.delete_ns(ns)
    k8s.delete_ns(f"{ns}-probe")
    ns_yaml = k8s.render(paths.MANIFESTS / "worker-ns.yaml.tmpl", NS=ns, RUN_ID=run.id)
    job_yaml = k8s.render(paths.MANIFESTS / "worker-job.yaml.tmpl", NS=ns, DEADLINE=DEADLINE,
                          WORKER_IMAGE=imgs["worker"], PILOT_MODEL=cfg["PILOT_MODEL"],
                          SPEND_CAP=cfg["PILOT_SPEND_CAP_USD"], TOKEN_CAP=cfg["PILOT_TOKEN_CAP"])
    (adir / "manifests.yaml").write_text(ns_yaml + "\n---\n" + job_yaml)  # no Secret data
    started = evidence.now()
    handle = None
    try:
        k8s.apply(ns_yaml)
        k8s.create_secret_from_files(ns, "model-key", cfg.model_files)
        k8s.create_configmap(ns, "inputs", {"base.bundle": idir / "base.bundle", "prompt.md": idir / "prompt.md",
                                            "meta.json": idir / "meta.json"})
        handle = runner.submit("worker", ns, "worker", job_yaml)
        att["state"] = "running"
        run.event("attempt", task, n, "attempt_running", imgs["worker"])
        if checks:
            checks.run_worker_checks(run, imgs, task, n, ns)
        outcome = runner.wait(handle, DEADLINE + 90)
        evidence.write_json(adir / "job.json", {"outcome": outcome, **runner.status(handle)})
        log = runner.collect(handle)
        (adir / "proxy-denials.log").write_text(proxy_denials(started))
        files, err = frame.decode(log)
        if files:
            (adir / "report.json").write_bytes(files["report.json"])
            if "change.bundle" in files:
                (adir / "change.bundle").write_bytes(files["change.bundle"])
            report = json.loads(files["report.json"])
            att["spend"] = report.get("spend")
            att["harness_exit"] = (report.get("harness") or {}).get("exit")
            att["changed_paths"] = report.get("changed_paths") or []
        att["state"] = "collected"
        if outcome == "DeadlineExceeded":
            att.update(state="failed", reason="deadline")
        elif outcome == "Timeout":
            att.update(state="failed", reason="deadline")
        elif err:
            att.update(state="failed", reason=err)
        elif (att.get("spend") or {}).get("stopped_by_cap"):
            att.update(state="failed", reason="spend_cap")
    except Exception as e:  # noqa: BLE001
        att.update(state="failed", reason="harness_error")
        run.event("attempt", task, n, "attempt_error", f"{e.__class__.__name__}: {str(e)[:300]}")
    finally:
        if handle:
            runner.delete(handle)
        else:
            k8s.delete_ns(ns)
        k8s.delete_ns(f"{ns}-probe", wait=False)
    run.event("attempt", task, n, f"attempt_{att['state']}", att.get("reason") or "")
    return att


def base_bundle(run, task: str, n: int) -> Path:
    return paths.BUILD / "inputs" / run.id / f"{task}-{n}" / "base.bundle"
