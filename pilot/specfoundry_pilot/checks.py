"""Live isolation and credential checks P01-P10 and the gate fail-closed matrix GM01-GM04
(contracts/evidence-record.md). Network probes run from a *probe twin*: a namespace rendered
from the same worker template (same labels, policies, quota) holding a sleeping tools pod,
because the worker namespace itself admits only one pod. 001-style control probes prove that
"blocked" results come from policy, not from the network."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from . import gate, k8s, paths

FILE = "checks/results.jsonl"
SCM_RE = re.compile(r"TOKEN|GITHUB|^GH_|PASSWORD", re.I)
# The pilot's own, non-credential env names (e.g. PILOT_TOKEN_CAP is a spend cap, not a token).
PILOT_ENV = {"PILOT_MODEL", "PILOT_SPEND_CAP_USD", "PILOT_TOKEN_CAP", "HTTPS_PROXY", "https_proxy", "NO_PROXY"}
CONTROL = ("pilot-control", "control")
STANDIN = "http://target.pilot-grader-standin.svc.cluster.local:8080/"
MODEL_PROXY = "http://proxy.pilot-egress-model.svc.cluster.local:8888"


def _curl(ns, pod, url, proxy=None) -> str:
    args = ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "8"]
    if proxy:
        args += ["-x", proxy]
    r = k8s.exec_(ns, pod, *args, url, timeout=30)
    code = (r.stdout or "").strip() or "000"
    return code


def reach(ns, pod, url, proxy=None) -> tuple[bool, str]:
    c = _curl(ns, pod, url, proxy)
    return c != "000", f"http={c}"


def blocked(ns, pod, url, proxy=None) -> tuple[bool, str]:
    c = _curl(ns, pod, url, proxy)
    return c == "000", f"http={c}"


def _rec(run, id_, req, ok, desc, unit, detail=""):
    run.record_check(FILE, id_, req, "pass" if ok else "fail", desc, f"{unit} {detail}".strip())


def _wait_pod(ns, label="app=worker", timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        pods = (k8s.get_json("-n", ns, "get", "pods", "-l", label, check=False) or {}).get("items", [])
        if pods:
            return pods[0]
        time.sleep(2)
    return None


def run_worker_checks(run, imgs: dict, task: str, n: int, ns: str) -> None:
    unit = f"{task}-{n}"
    twin = f"{ns}-probe"
    sa = f"system:serviceaccount:{ns}:worker"
    pod = _wait_pod(ns)
    if pod:
        k8s.wait_pod_ready(ns, pod["metadata"]["name"], 120)
    # P01 one pod, one container
    pods = (k8s.get_json("-n", ns, "get", "pods", check=False) or {}).get("items", [])
    conts = len(pod["spec"]["containers"]) if pod else 0
    _rec(run, "P01", "FR-005", len(pods) == 1 and conts == 1, "worker namespace has exactly 1 pod with 1 container",
         unit, f"pods={len(pods)} containers={conts}")
    # P02 no token
    sa_obj = k8s.get_json("-n", ns, "get", "sa", "worker", check=False) or {}
    tok = None
    if pod:
        r = k8s.exec_(ns, pod["metadata"]["name"], "sh", "-c",
                      "test ! -e /var/run/secrets/kubernetes.io/serviceaccount/token && echo absent", timeout=20)
        tok = r.stdout.strip() or ("pod-finished" if r.returncode else "present")
    ok = (sa_obj.get("automountServiceAccountToken") is False and pod is not None
          and pod["spec"].get("automountServiceAccountToken") is False and tok in ("absent", "pod-finished"))
    _rec(run, "P02", "FR-006", ok, "SA and pod automount off; no token file", unit, f"token={tok}")
    # P03 policies, quota, deadline
    np = k8s.get_json("-n", ns, "get", "netpol", "default-deny-all", check=False) or {}
    q = ((k8s.get_json("-n", ns, "get", "resourcequota", "worker-quota", check=False) or {}).get("spec") or {}).get("hard", {})
    job = k8s.get_json("-n", ns, "get", "job", "worker", check=False) or {}
    dl = (job.get("spec") or {}).get("activeDeadlineSeconds")
    ok = (set((np.get("spec") or {}).get("policyTypes", [])) == {"Ingress", "Egress"}
          and q.get("pods") == "1" and q.get("count/secrets") == "1" and bool(dl))
    _rec(run, "P03", "FR-006", ok, "default-deny netpol, quota pods=1 secrets=1, Job deadline", unit, f"quota={q} deadline={dl}")
    # P04 only model-key Secret; no SCM-like names in secret keys or env
    secrets = (k8s.get_json("-n", ns, "get", "secrets", check=False) or {}).get("items", [])
    names = [s["metadata"]["name"] for s in secrets]
    keys = [k for s in secrets for k in (s.get("data") or {})]
    envs = [e["name"] for c in (pod or {}).get("spec", {}).get("containers", []) for e in c.get("env", [])]
    bad = [x for x in keys + envs if SCM_RE.search(x) and x not in PILOT_ENV]
    _rec(run, "P04", "FR-007", names == ["model-key"] and not bad and pod is not None,
         "only Secret is model-key; no SCM-like secret keys or env names", unit, f"secrets={names} keys={keys} bad={bad}")
    # P05 no grading material
    cms = [c["metadata"]["name"] for c in (k8s.get_json("-n", ns, "get", "configmaps", check=False) or {}).get("items", [])]
    mounts = [m["mountPath"] for c in (pod or {}).get("spec", {}).get("containers", []) for m in c.get("volumeMounts", [])]
    _rec(run, "P05", "FR-007", "grading" not in cms and not any(m.startswith("/grading") for m in mounts),
         "no grading material in the worker namespace", unit, f"configmaps={cms}")
    # P06/P07 network, from the probe twin
    try:
        k8s.delete_ns(twin)
        k8s.apply(k8s.render(paths.MANIFESTS / "worker-ns.yaml.tmpl", NS=twin, RUN_ID=run.id))
        k8s.apply(k8s.render(paths.MANIFESTS / "worker-probe.yaml.tmpl", NS=twin, TOOLS_IMAGE=imgs["tools"]))
        ready = k8s.wait_pod_ready(twin, "probe", 120)
        mh = paths.MODEL_HOST.read_text().strip() if paths.MODEL_HOST.exists() else ""
        host = (os.environ.get("PILOT_PROBE_MODEL_URL") or f"https://{mh}/").rstrip("/") + "/"
        m_ok, m_d = reach(twin, "probe", host, MODEL_PROXY) if ready else (False, "probe not ready")
        g_ok, g_d = blocked(twin, "probe", "https://github.com/", MODEL_PROXY) if ready else (False, "")
        d_ok, d_d = blocked(twin, "probe", "https://1.1.1.1/") if ready else (False, "")
        c_ok, c_d = reach(*CONTROL, "https://github.com/")
        _rec(run, "P06", "FR-009b", m_ok and g_ok and d_ok and c_ok,
             "model host via proxy reachable; github.com via proxy and direct internet blocked; control reaches github.com",
             unit, f"model={m_d} github_via_proxy={g_d} direct={d_d} control={c_d}")
        s_ok, s_d = blocked(twin, "probe", STANDIN) if ready else (False, "")
        sc_ok, sc_d = reach(*CONTROL, STANDIN)
        _rec(run, "P07", "FR-010", s_ok and sc_ok, "worker-policy pod cannot reach the grader stand-in; control can",
             unit, f"twin={s_d} control={sc_d}")
    finally:
        k8s.delete_ns(twin, wait=False)
    # P08 RBAC
    gns = f"pilot-g-{task.lower()}-{n}"
    ans = {r: k8s.can_i("create", r, gns, sa) for r in ("pods", "configmaps", "pods/exec")}
    ans["patch-configmaps"] = k8s.can_i("patch", "configmaps", gns, sa)
    _rec(run, "P08", "FR-010", all(v == "no" for v in ans.values()), "worker SA cannot create/patch/exec in its grader namespace",
         unit, json.dumps(ans, sort_keys=True))


def run_cluster_checks(run, imgs: dict) -> None:
    # P09: only pilot-publish/scm-token holds an SCM-like credential.
    secrets = (k8s.get_json("get", "secrets", "-A", check=False) or {}).get("items", [])
    holders = sorted({f"{s['metadata']['namespace']}/{s['metadata']['name']}" for s in secrets
                      if s["metadata"]["namespace"].startswith("pilot-")
                      and any(SCM_RE.search(k) for k in (s.get("data") or {}))})
    _rec(run, "P09", "FR-013", holders == ["pilot-publish/scm-token"], "only pilot-publish holds an SCM credential",
         "cluster", f"holders={holders}")
    # P10: every pilot pod is digest-pinned, non-root, no privilege escalation.
    bad = []
    pods = (k8s.get_json("get", "pods", "-A", check=False) or {}).get("items", [])
    for p in pods:
        ns = p["metadata"]["namespace"]
        if not ns.startswith("pilot-"):
            continue
        psc = p["spec"].get("securityContext") or {}
        for c in p["spec"]["containers"]:
            sc = c.get("securityContext") or {}
            nonroot = sc.get("runAsNonRoot", psc.get("runAsNonRoot")) is True
            if "@sha256:" not in c["image"] or not nonroot or sc.get("allowPrivilegeEscalation") is not False:
                bad.append(f"{ns}/{p['metadata']['name']}/{c['name']}")
    _rec(run, "P10", "S6", not bad, "pilot pods digest-pinned, non-root, no privilege escalation", "cluster",
         f"pods={sum(1 for p in pods if p['metadata']['namespace'].startswith('pilot-'))} bad={bad}")


def gate_matrix(run) -> None:
    """GM01 unit matrix; GM02-GM04 live fail-closed variants (SC-005)."""
    env = {**os.environ, "PYTHONPATH": str(paths.PILOT)}
    r = subprocess.run(["python3", "-m", "unittest", "discover", "-s", str(paths.PILOT / "tests"), "-t", str(paths.PILOT),
                        "-p", "test_gate.py"], capture_output=True, text=True, env=env, timeout=300)
    tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
    _rec(run, "GM01", "FR-002", r.returncode == 0, "gate unit matrix (all refusal cases refuse)", "gate", tail[0])
    with tempfile.TemporaryDirectory() as t:
        d = gate.evaluate("A", "001", t, seq=0, repo="variant:no-roadmap")
        _rec(run, "GM02", "FR-002", d["decision"] == "refuse", "missing roadmap refuses", "gate", ",".join(d["reasons"]))
        shutil.copytree(paths.FIXTURE_TEMPLATE, Path(t) / "fx")
        d = gate.evaluate("A", "001", Path(t) / "fx", seq=0, repo="variant:tool-error", spec_bin="/bin/false")
        _rec(run, "GM03", "FR-002", d["decision"] == "refuse", "status tool error refuses", "gate", ",".join(d["reasons"]))
        rm = Path(t) / "fx/.specify/memory/roadmap.md"
        text = rm.read_text()
        rm.write_text(text[: text.index("### 002")] + "### 002 — Unique sl")
        d = gate.evaluate("B", "002", Path(t) / "fx", seq=0, repo="variant:truncated")
        _rec(run, "GM04", "FR-002", d["decision"] == "refuse", "truncated roadmap refuses B", "gate", ",".join(d["reasons"]))
