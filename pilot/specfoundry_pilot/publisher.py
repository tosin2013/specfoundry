"""Publish a passing attempt as one draft PR through the publisher Job (FR-012-FR-016, R8)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import evidence, fixture, frame, k8s, paths

TIMEOUT = 300


class PublishError(Exception):
    pass


def prs(run) -> list:
    p = run.dir / "prs.json"
    return json.loads(p.read_text()) if p.exists() else []


def _body(run, task: str, n: int) -> str:
    st = run.task(task)
    rows = "\n".join(f"| {a['n']} | {a.get('induction') or '-'} | {a.get('result', '-')} | "
                     f"{(a.get('spend') or {}).get('cost_usd', '-')} | {(a.get('spend') or {}).get('tokens', '-')} |"
                     for a in st.get("attempts", []))
    gates = ", ".join(str(g) for g in st.get("gate_seqs", []))
    imgs = json.loads(paths.IMAGES_JSON.read_text())
    return (f"Opened by the specfoundry M1 pilot **publisher** (run `{run.id}`, task {task}, "
            f"fixture item {paths.TASKS[task]}).\n\n"
            f"Passing attempt: **{n}**. Gate decisions: {gates or '-'}.\n\n"
            f"| Attempt | Induction | Grade | Cost (USD) | Tokens |\n|---|---|---|---|---|\n{rows}\n\n"
            f"Images: worker `{imgs['worker']}`, grader/publisher `{imgs['tools']}`.\n\n"
            f"Evidence: `specs/002-m1-gated-pilot/evidence/{run.id}/` in the specfoundry repository.\n\n"
            f"This is a **draft**. A human reviews and merges it; the pilot never merges.\n")


def publish(run, cfg, imgs: dict, runner, task: str, n: int) -> dict:
    adir = run.attempt_dir(task, n)
    g = json.loads((adir / "grade.json").read_text())
    if g.get("result") != "pass":
        raise PublishError(f"attempt {task}/{n} did not pass grading (FR-012)")
    existing = [p for p in prs(run) if p["task"] == task]
    if existing:
        return existing[0]
    head = f"pilot/{run.id}/{task.lower()}"
    spec = {"repo": cfg.repo, "head": head, "base": cfg.branch, "base_revision": g_base(adir),
            "title": f"pilot {run.id} task {task}", "body": _body(run, task, n), "run_id": run.id, "task": task}
    cm = f"pub-{task.lower()}"
    jobname = f"publish-{task.lower()}-{run.id.lower().replace('t', '').replace('z', '')[-8:]}"
    run.event("publish", task, n, "publish_started", head)
    k8s.kubectl("-n", "pilot-publish", "delete", "configmap", cm, "--ignore-not-found", check=False)
    k8s.kubectl("-n", "pilot-publish", "delete", "job", jobname, "--ignore-not-found", "--wait=true", check=False)
    with tempfile.TemporaryDirectory() as t:
        Path(t, "pr.json").write_text(json.dumps(spec))
        k8s.create_configmap("pilot-publish", cm, {"pr.json": Path(t, "pr.json"), "change.bundle": adir / "change.bundle"})
    job = k8s.render(paths.MANIFESTS / "publisher-job.yaml.tmpl", JOB=jobname, CONFIGMAP=cm, TOOLS_IMAGE=imgs["tools"])
    handle = runner.submit("publisher", "pilot-publish", jobname, job, own_namespace=False)
    try:
        outcome = runner.wait(handle, TIMEOUT + 60)
        files, err = frame.decode(runner.collect(handle), required=("result.json",))
        status = runner.status(handle)
    finally:
        runner.delete(handle)
        k8s.kubectl("-n", "pilot-publish", "delete", "configmap", cm, "--ignore-not-found", check=False)
    if err or outcome != "Complete":
        detail = (json.loads(files["result.json"]).get("error") if files else None) or err or outcome
        raise PublishError(f"publisher {outcome}: {detail} ({status.get('pod_reason')})")
    res = json.loads(files["result.json"])
    if res.get("error"):
        raise PublishError(res["error"])
    view = json.loads(fixture.gh("pr", "view", str(res["number"]), "-R", cfg.repo, "--json",
                                 "isDraft,author,headRefName,url").stdout)
    operator = fixture.gh("api", "user", "--jq", ".login").stdout.strip()
    entry = {"task": task, "number": res["number"], "url": view["url"], "head": view["headRefName"],
             "draft": bool(view["isDraft"]), "author": view["author"]["login"],
             "publisher_identity": res.get("token_login"), "operator_login": operator,
             "attempt": n, "created": bool(res.get("created"))}
    if not entry["draft"] or entry["head"] != head:
        raise PublishError(f"PR #{entry['number']} is not the expected draft for {head}")
    allp = prs(run) + [entry]
    evidence.write_json(run.dir / "prs.json", allp)
    run.event("publish", task, n, "pr_opened" if entry["created"] else "pr_found", entry["url"])
    return entry


def g_base(adir: Path) -> str:
    return json.loads((adir / "meta.json").read_text())["base_revision"]
