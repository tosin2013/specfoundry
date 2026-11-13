"""Plain Kubernetes Jobs backend."""
from __future__ import annotations

from .. import k8s
from .base import Handle, Runner


class JobsRunner(Runner):
    def submit(self, kind, namespace, name, manifest, own_namespace=True) -> Handle:
        k8s.apply(manifest)
        return Handle(kind=kind, namespace=namespace, name=name, own_namespace=own_namespace)

    def wait(self, handle, timeout):
        return k8s.wait_job(handle.namespace, handle.name, timeout)

    def collect(self, handle):
        return k8s.logs(handle.namespace, handle.name)

    def status(self, handle):
        job = k8s.get_json("-n", handle.namespace, "get", "job", handle.name, check=False) or {}
        pod = k8s.job_pod(handle.namespace, handle.name)
        pj = k8s.get_json("-n", handle.namespace, "get", "pod", pod, check=False) if pod else None
        term = None
        for cs in ((pj or {}).get("status", {}).get("containerStatuses") or []):
            term = (cs.get("state") or {}).get("terminated") or term
        return {"job_status": job.get("status"), "pod": pod,
                "pod_phase": (pj or {}).get("status", {}).get("phase"),
                "pod_reason": (pj or {}).get("status", {}).get("reason"),
                "container_terminated": term}

    def delete(self, handle):
        if handle.own_namespace:
            k8s.delete_ns(handle.namespace, wait=True)
        else:
            k8s.kubectl("-n", handle.namespace, "delete", "job", handle.name, "--ignore-not-found",
                        "--cascade=foreground", check=False, timeout=120)
