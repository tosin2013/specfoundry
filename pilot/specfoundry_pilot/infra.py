"""Long-lived pilot infrastructure applied by `pilot up`: egress proxies, publisher namespace
(+ its SCM Secret, created from the env-file path only), and check helpers."""
from __future__ import annotations

import re

from . import k8s, paths


def _indent(text: str, n: int = 4) -> str:
    return "\n".join((" " * n + line) if line else "" for line in text.splitlines())


def allowlist(hosts: list[str]) -> str:
    for h in hosts:
        if not re.fullmatch(r"[A-Za-z0-9.-]+", h):
            raise ValueError(f"bad egress host {h!r}")
    return "\n".join(f"^{re.escape(h)}$" for h in hosts) + "\n"


def render_egress(ns: str, client_role: str, hosts: list[str], image: str) -> str:
    conf = (paths.IMAGES / "egress" / "tinyproxy.conf.tmpl").read_text()
    return k8s.render(paths.MANIFESTS / "egress.yaml.tmpl", NS=ns, CLIENT_ROLE=client_role, IMAGE=image,
                      CONF=_indent(conf), ALLOWLIST=_indent(allowlist(hosts)))


def apply_all(cfg, imgs: dict) -> None:
    print("== egress proxies", flush=True)
    k8s.apply(render_egress("pilot-egress-model", "worker", cfg.model_hosts, imgs["egress"]))
    k8s.apply(render_egress("pilot-egress-scm", "publisher", ["github.com", "api.github.com"], imgs["egress"]))
    for ns in ("pilot-egress-model", "pilot-egress-scm"):
        r = k8s.kubectl("-n", ns, "rollout", "status", "deploy/proxy", "--timeout=180s", check=False, timeout=200)
        if r.returncode != 0:
            fail_on_pull(ns, f"egress proxy in {ns} did not become ready")

    print("== publisher namespace", flush=True)
    k8s.apply((paths.MANIFESTS / "publisher-ns.yaml.tmpl").read_text())
    k8s.kubectl("-n", "pilot-publish", "delete", "secret", "scm-token", "--ignore-not-found")
    k8s.create_secret_from_env_file("pilot-publish", "scm-token", cfg.publisher_env)

    print("== check helpers", flush=True)
    k8s.apply(k8s.render(paths.MANIFESTS / "infra.yaml.tmpl", TOOLS_IMAGE=imgs["tools"]))
    for ns, pod in (("pilot-control", "control"), ("pilot-grader-standin", "target")):
        if not k8s.wait_pod_ready(ns, pod):
            fail_on_pull(ns, f"{ns}/{pod} not ready")


def fail_on_pull(ns: str, what: str) -> None:
    """Fail closed with the image reference when a pull failed (no fallback to local builds)."""
    errs = k8s.pull_errors(ns)
    if errs:
        raise RuntimeError(f"{what}: image pull failed: {'; '.join(errs)}. "
                           "Check pilot/images.lock and registry access; no local-build fallback is attempted.")
    raise RuntimeError(what)
