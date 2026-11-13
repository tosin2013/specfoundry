"""kubectl subprocess helpers bound to the pilot cluster context."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from string import Template

from . import paths


class K8sError(Exception):
    pass


def kubectl(*args, input: str | None = None, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
    cmd = ["kubectl", "--context", paths.CONTEXT, *args]
    r = subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise K8sError(f"{' '.join(args[:4])}…: {r.stderr.strip()[:500]}")
    return r


def get_json(*args, check: bool = True):
    r = kubectl(*args, "-o", "json", check=check)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def apply(yaml_text: str) -> None:
    kubectl("apply", "-f", "-", input=yaml_text)


def render(template_path: Path, **vars) -> str:
    """${VAR} substitution; a missing variable is an error."""
    return Template(Path(template_path).read_text()).substitute(**{k: str(v) for k, v in vars.items()})


def wait_job(ns: str, name: str, timeout: int) -> str:
    """Return Complete | Failed | DeadlineExceeded | Timeout."""
    end = time.time() + timeout
    while time.time() < end:
        job = get_json("-n", ns, "get", "job", name, check=False)
        for c in (job or {}).get("status", {}).get("conditions", []) or []:
            if c.get("status") != "True":
                continue
            if c.get("type") == "Complete":
                return "Complete"
            if c.get("type") == "Failed":
                return "DeadlineExceeded" if c.get("reason") == "DeadlineExceeded" else "Failed"
        time.sleep(3)
    return "Timeout"


def job_pod(ns: str, job: str) -> str | None:
    pods = get_json("-n", ns, "get", "pods", "-l", f"job-name={job}", check=False) or {}
    items = pods.get("items", [])
    return items[0]["metadata"]["name"] if items else None


def logs(ns: str, job: str, container: str | None = None) -> str:
    pod = job_pod(ns, job)
    if not pod:
        return ""
    args = ["-n", ns, "logs", pod]
    if container:
        args += ["-c", container]
    r = kubectl(*args, check=False, timeout=60)
    return r.stdout


def delete_ns(ns: str, wait: bool = True) -> None:
    kubectl("delete", "namespace", ns, "--ignore-not-found", f"--wait={'true' if wait else 'false'}",
            check=False, timeout=300)


def ns_exists(ns: str) -> bool:
    return kubectl("get", "namespace", ns, check=False).returncode == 0


def create_secret_from_env_file(ns: str, name: str, path: Path) -> None:
    """Pass the path only; the value never enters this process."""
    kubectl("-n", ns, "create", "secret", "generic", name, f"--from-env-file={path}")


def create_secret_from_files(ns: str, name: str, files: list[Path]) -> None:
    """Pass paths only; contents never enter this process."""
    kubectl("-n", ns, "create", "secret", "generic", name, *[f"--from-file={Path(f).name}={f}" for f in files])


def create_configmap(ns: str, name: str, files: dict[str, Path], labels: dict | None = None) -> None:
    args = ["-n", ns, "create", "configmap", name] + [f"--from-file={k}={v}" for k, v in files.items()]
    kubectl(*args)
    if labels:
        kubectl("-n", ns, "label", "configmap", name, *[f"{k}={v}" for k, v in labels.items()])


def can_i(verb: str, resource: str, ns: str, as_sa: str) -> str:
    r = kubectl("auth", "can-i", verb, resource, "-n", ns, f"--as={as_sa}", check=False)
    return r.stdout.strip() or r.stderr.strip()


def exec_(ns: str, pod: str, *cmd, timeout: int = 30) -> subprocess.CompletedProcess:
    return kubectl("-n", ns, "exec", pod, "--", *cmd, check=False, timeout=timeout)


def wait_pod_ready(ns: str, pod: str, timeout: int = 180) -> bool:
    return kubectl("-n", ns, "wait", "--for=condition=Ready", f"pod/{pod}", f"--timeout={timeout}s",
                   check=False, timeout=timeout + 10).returncode == 0
