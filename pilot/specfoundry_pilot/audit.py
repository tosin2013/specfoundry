"""Evidence-only audit AU01-AU11 + redaction scan (contracts/evidence-record.md, R12).

Reads only files in the run directory. Secret values are matched with `grep -F -f <file>`
so they never enter this process.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from . import evidence, prompt

PATTERNS = r"github_pat_[A-Za-z0-9_]{10,}|gh[pousr]_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9_-]{16,}|Bearer [A-Za-z0-9._-]{16,}"


def redaction_scan(root: Path, key_files: list[Path], env_files: list[Path]) -> list[str]:
    hits = set()
    r = subprocess.run(["grep", "-rlE", PATTERNS, str(root)], capture_output=True, text=True)
    hits.update(l for l in r.stdout.splitlines() if l)
    for kf in key_files:
        if kf.exists() and kf.stat().st_size > 0:
            r = subprocess.run(["grep", "-rlF", "-f", str(kf), str(root)], capture_output=True, text=True)
            hits.update(l for l in r.stdout.splitlines() if l)
    for ef in env_files:
        if ef.exists():
            r = subprocess.run(["bash", "-c", 'grep -rlF -f <(grep -v "^[[:space:]]*#" "$1" | grep "=" | cut -d= -f2- | grep -v "^$") "$2"',
                                "_", str(ef), str(root)], capture_output=True, text=True)
            hits.update(l for l in r.stdout.splitlines() if l)
    return sorted(str(Path(h).relative_to(root)) for h in hits)


def _row(id_, ok, desc, detail=""):
    return evidence.check_row(id_, "audit", "pass" if ok else "fail", desc, detail)


def _attempts(d: Path):
    out = []
    for a in sorted((d / "attempts").glob("*-*")):
        task, n = a.name.split("-", 1)
        out.append((task, int(n), a))
    return out


def audit_dir(d: Path, secret_files: list[Path] | None = None, env_files: list[Path] | None = None,
              final: bool = True) -> list[dict]:
    ev = evidence.read_jsonl(d / "events.jsonl")
    checks = evidence.read_jsonl(d / "checks" / "results.jsonl")
    rows = []

    def idx(pred):
        return next((i for i, e in enumerate(ev) if pred(e)), None)

    # AU01: B never started (or allowed) before A verified; at least one refusal of B.
    v = idx(lambda e: e["event"] == "task_verified" and e["task"] == "A")
    cut = v if v is not None else len(ev)
    before = ev[:cut]
    b_attempts = [e for e in before if e["task"] == "B" and e["stage"] == "attempt"]
    b_allows = [e for e in before if e["task"] == "B" and e["event"] == "gate_allow"]
    b_refusals = [e for e in before if e["task"] == "B" and e["event"] == "gate_refuse"]
    rows.append(_row("AU01", not b_attempts and not b_allows and b_refusals,
                     "B refused (and never attempted) until A verified (SC-001)",
                     f"refusals={len(b_refusals)} attempts_before={len(b_attempts)} allows_before={len(b_allows)}"))

    # AU02: A/1 fail -> A/n>=2 pass -> B pass, in order.
    grades = [(e["task"], e["attempt"], e["event"]) for e in ev if e["stage"] == "grade" and e["event"] in ("grade_pass", "grade_fail")]
    ok2 = False
    if grades and grades[0] == ("A", 1, "grade_fail"):
        a_pass = next((i for i, g in enumerate(grades) if g[0] == "A" and g[2] == "grade_pass" and g[1] >= 2), None)
        b_pass = next((i for i, g in enumerate(grades) if g[0] == "B" and g[2] == "grade_pass"), None)
        ok2 = a_pass is not None and b_pass is not None and a_pass < b_pass
    rows.append(_row("AU02", ok2, "order A/1 fail -> A/2+ pass -> B pass (SC-002)", str(grades)))

    # AU03: exactly 2 PRs, one per task, draft, authored by the publisher identity.
    prs = json.loads((d / "prs.json").read_text()) if (d / "prs.json").exists() else []
    ok3 = (len(prs) == 2 and sorted(p.get("task") for p in prs) == ["A", "B"]
           and all(p.get("draft") is True and p.get("author") and p.get("author") == p.get("publisher_identity") for p in prs))
    rows.append(_row("AU03", ok3, "exactly 2 draft PRs, both by the publisher identity (SC-003)",
                     json.dumps([{k: p.get(k) for k in ("task", "number", "draft", "author", "publisher_identity")} for p in prs])))

    # AU04: credential checks present and passing.
    cred = [r for r in checks if r["id"] in ("P04", "P09")]
    ok4 = bool([r for r in cred if r["id"] == "P04"]) and bool([r for r in cred if r["id"] == "P09"]) and all(r["result"] == "pass" for r in cred)
    rows.append(_row("AU04", ok4, "no worker/grader held an SCM credential (P04, P09) (SC-004)", f"rows={len(cred)}"))

    # AU05: gate fail-closed matrix.
    gm = [r for r in checks if r["id"].startswith("GM")]
    rows.append(_row("AU05", bool(gm) and all(r["result"] == "pass" for r in gm), "gate fail-closed matrix passed (SC-005)", f"rows={len(gm)}"))

    # AU06: spend within cap per attempt.
    bad6 = []
    for task, n, a in _attempts(d):
        rp = a / "report.json"
        if not rp.exists():
            continue
        sp = json.loads(rp.read_text()).get("spend")
        if sp is None:
            continue  # harness never ran
        within = (sp["cost_usd"] <= sp["cap_usd"]) if sp.get("cap_mode") == "cost" else (sp["tokens"] <= sp["token_cap"])
        if not (within or sp.get("stopped_by_cap")):
            bad6.append(f"{task}-{n}")
    rows.append(_row("AU06", not bad6, "every attempt within its spend cap (SC-008)", f"over={bad6}"))

    # AU07: teardown verified.
    td = evidence.read_jsonl(d / "teardown.jsonl")
    if final or td:
        rows.append(_row("AU07", bool(td) and all(r["result"] == "pass" for r in td), "teardown verified (SC-006)", f"rows={len(td)}"))

    # AU08: redaction scan.
    hits = redaction_scan(d, secret_files or [], env_files or [])
    rows.append(_row("AU08", not hits, "no secrets in the evidence record", f"hits={hits}"))

    # AU09: every retry was confirmed by the operator.
    bad9 = []
    for i, e in enumerate(ev):
        if e["stage"] == "attempt" and e["event"] == "attempt_created" and (e["attempt"] or 1) > 1:
            if not any(x["event"] == "retry_confirmed" and x["task"] == e["task"] and x["attempt"] == e["attempt"] for x in ev[:i]):
                bad9.append(f"{e['task']}-{e['attempt']}")
    rows.append(_row("AU09", not bad9, "every retry confirmed by the operator (FR-017)", f"unconfirmed={bad9}"))

    # AU10: mode confirmed before the first attempt.
    m = idx(lambda e: e["event"] == "mode_confirmed")
    a = idx(lambda e: e["stage"] == "attempt")
    rows.append(_row("AU10", m is not None and (a is None or m < a), "mode confirmed before any worker staged (FR-023)", f"mode_seq={m} first_attempt={a}"))

    # AU11: induction only on A/1, and it withheld exactly the acceptance section.
    bad11 = []
    a2_sha = None
    for task, n, ad in _attempts(d):
        p = (ad / "prompt.md").read_text() if (ad / "prompt.md").exists() else None
        induced = (ad / "induction.json").exists()
        if p is None:
            bad11.append(f"{task}-{n}:no prompt")
            continue
        if (task, n) == ("A", 1):
            if not induced or prompt.HEADING in p:
                bad11.append("A-1:not induced")
        else:
            if induced or prompt.HEADING not in p:
                bad11.append(f"{task}-{n}:induced or missing section")
            elif (task, n) == ("A", 2):
                a2_sha = prompt.section_sha256(p)
    a1 = d / "attempts" / "A-1" / "induction.json"
    if a1.exists() and a2_sha and json.loads(a1.read_text()).get("removed_sha256") != a2_sha:
        bad11.append("A-1 removed span != A-2 section")
    rows.append(_row("AU11", not bad11, "induction applied to A/1 only, withholding exactly the acceptance section", f"{bad11}"))
    return rows


def run(run_obj, final: bool = False, cfg=None) -> bool:
    if cfg is None:
        try:
            from . import config
            cfg = config.load(require_secrets=False, guard=False)
        except Exception:  # noqa: BLE001
            cfg = None
    key_files = [p for p in (cfg.model_files if cfg else []) if p.name != "opencode.json" and p.exists()]
    env_files = [cfg.publisher_env] if cfg and cfg.publisher_env.exists() else []
    rows = audit_dir(run_obj.dir, key_files, env_files, final=final)
    out = run_obj.dir / "audit.jsonl"
    if out.exists():
        out.unlink()
    for r in rows:
        evidence.append_jsonl(out, r)
        print(f"  {'PASS' if r['result'] == 'pass' else 'FAIL'} {r['id']} {r['description']}")
    run_obj.event("audit", None, None, "audit_done", f"{sum(r['result'] == 'pass' for r in rows)}/{len(rows)}")
    evidence.write_summary(run_obj)
    return all(r["result"] == "pass" for r in rows)
