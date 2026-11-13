"""`pilot up` / `pilot down`: kind + Calico + local registry + pilot infrastructure."""
from __future__ import annotations

import json
import os
import subprocess

from . import evidence, k8s, paths


def sh(*args, check=True, timeout=600, **kw) -> subprocess.CompletedProcess:
    r = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout, **kw)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}: {(r.stderr or r.stdout).strip()[:800]}")
    return r


def say(msg: str) -> None:
    print(f"== {msg}", flush=True)


def cluster_exists() -> bool:
    r = sh("kind", "get", "clusters", check=False)
    return paths.CLUSTER in r.stdout.split()


def registry_running() -> bool:
    r = sh("docker", "inspect", "-f", "{{.State.Running}}", paths.REGISTRY_NAME, check=False)
    return r.stdout.strip() == "true"


def up_cluster() -> None:
    pins = paths.read_pins()
    paths.BUILD.mkdir(parents=True, exist_ok=True)
    say("pinned tools")
    sh("bash", str(paths.ROOT / "test/isolation/tools.sh"),
       env={**os.environ, "KIND_VERSION": pins["KIND_VERSION"], "KUBECTL_VERSION": pins["KUBECTL_VERSION"]})

    say("local registry")
    if not registry_running():
        sh("docker", "rm", "-f", paths.REGISTRY_NAME, check=False)
        sh("docker", "run", "-d", "--restart=no", "--name", paths.REGISTRY_NAME,
           "-p", "127.0.0.1:5001:5000", pins["REGISTRY_IMAGE"])

    say(f"kind cluster {paths.CLUSTER}")
    if not cluster_exists():
        sh("kind", "create", "cluster", "--config", str(paths.PILOT / "kind-config.yaml"), "--wait", "0s", timeout=900)
    node = f"{paths.CLUSTER}-control-plane"
    d = f"/etc/containerd/certs.d/{paths.REGISTRY_HOST}"
    sh("docker", "exec", node, "mkdir", "-p", d)
    sh("docker", "exec", "-i", node, "cp", "/dev/stdin", f"{d}/hosts.toml",
       input=f'[host."http://{paths.REGISTRY_NAME}:5000"]\n')
    sh("docker", "network", "connect", "kind", paths.REGISTRY_NAME, check=False)

    say(f"calico {pins['CALICO_VERSION']}")
    calico = paths.BUILD / "calico.yaml"
    sh("curl", "-fsSL", "-o", str(calico),
       f"https://raw.githubusercontent.com/projectcalico/calico/{pins['CALICO_VERSION']}/manifests/calico.yaml")
    (paths.BUILD / "calico.sha256").write_text(evidence.sha256_file(calico) + "\n")
    k8s.kubectl("apply", "-f", str(calico), timeout=300)
    for args in (["-n", "kube-system", "rollout", "status", "ds/calico-node", "--timeout=300s"],
                 ["-n", "kube-system", "rollout", "status", "deploy/calico-kube-controllers", "--timeout=300s"],
                 ["wait", "--for=condition=Ready", "node", "--all", "--timeout=180s"],
                 ["-n", "kube-system", "rollout", "status", "deploy/coredns", "--timeout=180s"]):
        k8s.kubectl(*args, timeout=360)


def up(cfg, cluster_only: bool = False) -> None:
    paths.UP_OK.unlink(missing_ok=True)
    if not cluster_only:
        from . import publisher_token
        res = publisher_token.verify(cfg)
        publisher_token.report(res)
        if not res.get("ok"):
            raise RuntimeError("publisher token check failed; fix it with `pilot publisher-token`")
    up_cluster()
    if cluster_only:
        say("cluster only: skipping images, proxies and publisher")
        return
    from . import images, infra  # late import: these need the full pilot config
    imgs = images.build_all()
    infra.apply_all(cfg, imgs)
    paths.UP_OK.write_text(json.dumps({"at": evidence.now(), "images": imgs}) + "\n")
    say("up complete")


def teardown_rows() -> list[dict]:
    rows = []
    c = not cluster_exists()
    rows.append(evidence.check_row("T01", "N3", "pass" if c else "fail", "kind cluster deleted", "absent" if c else "present"))
    n = sh("docker", "ps", "-a", "--filter", f"label=io.x-k8s.kind.cluster={paths.CLUSTER}", "-q", check=False).stdout.split()
    rows.append(evidence.check_row("T02", "N3", "pass" if not n else "fail", "no kind node containers remain", f"containers={len(n)}"))
    r = sh("docker", "ps", "-a", "--filter", f"name=^{paths.REGISTRY_NAME}$", "-q", check=False).stdout.split()
    rows.append(evidence.check_row("T03", "N3", "pass" if not r else "fail", "local registry container removed", f"containers={len(r)}"))
    return rows


def down() -> int:
    say("teardown")
    sh("kind", "delete", "cluster", "--name", paths.CLUSTER, check=False, timeout=300)
    sh("docker", "rm", "-f", paths.REGISTRY_NAME, check=False)
    paths.UP_OK.unlink(missing_ok=True)
    rows = teardown_rows()
    run = evidence.load_run()
    target = (run.dir / "teardown.jsonl") if run else (paths.BUILD / "teardown.jsonl")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()  # one teardown record per run: the latest
    for row in rows:
        evidence.append_jsonl(target, row)
        print(f"  {'PASS' if row['result'] == 'pass' else 'FAIL'} {row['id']} {row['description']} ({row['detail']})")
    if run and run.state.get("state") in ("succeeded",):
        run.event("teardown", None, None, "torn_down", str(target.name))
    return 0 if all(r["result"] == "pass" for r in rows) else 1
