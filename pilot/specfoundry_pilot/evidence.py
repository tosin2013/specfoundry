"""Evidence record (contracts/evidence-record.md) and resumable run state (data-model Run)."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import subprocess
from pathlib import Path

from . import paths


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def check_row(id_, requirement, result, description, detail="") -> dict:
    return {"id": id_, "requirement": requirement, "result": result,
            "description": description, "detail": str(detail)[:2000]}


class Run:
    def __init__(self, dir_: Path):
        self.dir = dir_
        self.id = dir_.name
        self.state = json.loads((dir_ / "run.json").read_text()) if (dir_ / "run.json").exists() else {}

    # -- state -----------------------------------------------------------------
    def save(self) -> None:
        write_json(self.dir / "run.json", self.state)

    def task(self, label: str) -> dict:
        return self.state.setdefault("tasks", {}).setdefault(label, {"state": "pending", "attempts": []})

    def set_run_state(self, state: str, reason: str | None = None) -> None:
        self.state["state"] = state
        self.state["reason"] = reason
        self.save()
        self.event("run", None, None, f"run_{state}", reason or "")

    # -- events ----------------------------------------------------------------
    def _next(self, key: str) -> int:
        n = int(self.state.get(key, 0)) + 1
        self.state[key] = n
        self.save()
        return n

    def event(self, stage: str, task, attempt, event: str, detail="") -> dict:
        row = {"seq": self._next("event_seq"), "at": now(), "stage": stage, "task": task,
               "attempt": attempt, "event": event, "detail": detail}
        append_jsonl(self.dir / "events.jsonl", row)
        return row

    def events(self) -> list:
        return read_jsonl(self.dir / "events.jsonl")

    def next_gate_seq(self) -> int:
        return self._next("gate_seq")

    # -- files -----------------------------------------------------------------
    def attempt_dir(self, task: str, n: int) -> Path:
        d = self.dir / "attempts" / f"{task}-{n}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def record_check(self, file: str, id_, requirement, result, description, detail="") -> dict:
        row = check_row(id_, requirement, result, description, detail)
        append_jsonl(self.dir / file, row)
        mark = "PASS" if result == "pass" else "FAIL"
        print(f"  {mark} {id_:<5} {requirement:<8} {description}")
        return row


def new_run() -> Run:
    rid = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = paths.EVIDENCE_ROOT / rid
    for sub in ("gate", "attempts", "reconcile", "checks"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    run = Run(d)
    run.state = {"run_id": rid, "state": "in-progress", "reason": None, "created": now(),
                 "tasks": {}, "event_seq": 0, "gate_seq": 0}
    run.save()
    return run


def all_runs() -> list[Path]:
    if not paths.EVIDENCE_ROOT.exists():
        return []
    return sorted(p for p in paths.EVIDENCE_ROOT.iterdir() if (p / "run.json").exists())


def load_run(run_id: str | None = None) -> Run | None:
    if run_id:
        d = paths.EVIDENCE_ROOT / run_id
        return Run(d) if (d / "run.json").exists() else None
    runs = all_runs()
    return Run(runs[-1]) if runs else None


def active_run() -> Run | None:
    r = load_run()
    if r is None:
        return None
    s = str(r.state.get("state", ""))
    return r if s == "in-progress" or s.startswith("paused") else None


def write_config_json(run: Run, cfg) -> None:
    secrets = {}
    for p in list(cfg.model_files) + [cfg.publisher_env]:
        rel = p.relative_to(cfg.config_dir)
        secrets[str(rel)] = {"sha256": sha256_file(p) if p.exists() else None}
    write_json(run.dir / "config.json", {"pilot_env": cfg.public(), "secret_files": secrets})


def _cmd(args) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else ""
    except Exception as e:  # noqa: BLE001
        return f"unavailable ({e.__class__.__name__})"


def write_versions(run: Run, images: dict | None = None) -> None:
    pins = paths.read_pins()
    server = _cmd(["bash", "-c", f"kubectl --context {paths.CONTEXT} version -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)[\"serverVersion\"][\"gitVersion\"])'"])
    calico_sha = (paths.BUILD / "calico.sha256").read_text().strip() if (paths.BUILD / "calico.sha256").exists() else "unknown"
    lines = [
        f"run_id: {run.id}",
        f"kind: {_cmd(['kind', 'version'])}",
        f"kubectl: {_cmd(['kubectl', 'version', '--client'])}",
        f"server: {server}",
        f"node_image: {_cmd(['docker', 'inspect', '--format', '{{.Config.Image}}', paths.CLUSTER + '-control-plane'])}",
        f"calico: {pins['CALICO_VERSION']} sha256={calico_sha}",
        f"spec: {_cmd(['spec', '--version'])} sha256={pins['SPEC_SHA256']}",
        f"opencode: {pins['OPENCODE_VERSION']} sha256={pins['OPENCODE_SHA256']}",
        f"registry_image: {pins['REGISTRY_IMAGE']}",
    ]
    for k, v in sorted((images or {}).items()):
        lines.append(f"image_{k}: {v}")
    lines.append(f"host: {_cmd(['uname', '-srm'])}")
    (run.dir / "versions.txt").write_text("\n".join(lines) + "\n")


KNOWN_LIMITS = [
    "Gate runs on the host (no published spec-status CLI image yet, PRD §8 ask 3).",
    "Grader uses `spec status --json`, not `verify-readiness` (report-only skill mode not shipped, PRD §8 ask 1).",
    "Reconcile is a deterministic pilot equivalent of the spec-status reconcile skill.",
    "Spend cap is enforced by the pilot watchdog and deadline unless a provider-side cap is declared (R2).",
    "Single-node kind only; multi-node policy enforcement not covered.",
]


def write_summary(run: Run) -> Path:
    ev = run.events()
    st = run.state
    out = [f"# M1 pilot run {run.id}", "",
           f"**State:** {st.get('state')}" + (f" ({st.get('reason')})" if st.get("reason") else ""), ""]
    if ev:
        t0 = _dt.datetime.strptime(ev[0]["at"], "%Y-%m-%dT%H:%M:%SZ")
        t1 = _dt.datetime.strptime(ev[-1]["at"], "%Y-%m-%dT%H:%M:%SZ")
        wait = sum(int(e.get("detail") or 0) for e in ev if e["event"] == "merge_wait_seconds")
        out += [f"**Elapsed:** {int((t1 - t0).total_seconds())} s total, "
                f"{int((t1 - t0).total_seconds()) - wait} s excluding the human merge wait", ""]
    mode = st.get("mode")
    if mode:
        out += [f"**Mode:** `{json.dumps(mode, sort_keys=True)}`", ""]
    out += ["## Attempts", "", "| Task | Attempt | Induction | Grade | Cost (USD) | Tokens |", "|---|---|---|---|---|---|"]
    for label in ("A", "B"):
        for a in st.get("tasks", {}).get(label, {}).get("attempts", []):
            sp = a.get("spend") or {}
            out.append(f"| {label} | {a.get('n')} | {a.get('induction') or '-'} | {a.get('result', '-')}"
                       f"{' (' + a['reason'] + ')' if a.get('reason') else ''} | {sp.get('cost_usd', '-')} | {sp.get('tokens', '-')} |")
    prs = json.loads((run.dir / "prs.json").read_text()) if (run.dir / "prs.json").exists() else []
    out += ["", "## Draft PRs", ""] + [f"- Task {p['task']}: [{p['url']}]({p['url']}) (draft={p['draft']}, author={p['author']})" for p in prs]
    for name in ("checks/results.jsonl", "audit.jsonl", "teardown.jsonl"):
        rows = read_jsonl(run.dir / name)
        if rows:
            p = sum(r["result"] == "pass" for r in rows)
            out.append(f"- `{name}`: {p} of {len(rows)} pass")
    out += ["", "## Events", "", "| Seq | Stage | Task | Attempt | Event | Detail |", "|---|---|---|---|---|---|"]
    for e in ev:
        d = str(e.get("detail", "")).replace("|", "\\|").replace("\n", " ")[:120]
        out.append(f"| {e['seq']} | {e['stage']} | {e['task'] or ''} | {e['attempt'] or ''} | {e['event']} | {d} |")
    out += ["", "## Known limits", ""] + [f"- {l}" for l in KNOWN_LIMITS]
    p = run.dir / "summary.md"
    p.write_text("\n".join(out) + "\n")
    return p
