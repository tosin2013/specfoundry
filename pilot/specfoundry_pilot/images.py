"""Build the pilot images, push them to the local registry, and resolve digests (R10)."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from . import paths


def _sh(*args, timeout=1800):
    r = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])}: {(r.stderr or r.stdout).strip()[-1500:]}")
    return r.stdout


def _context(name: str, extra: dict[str, Path]) -> Path:
    ctx = paths.BUILD / f"ctx-{name}"
    shutil.rmtree(ctx, ignore_errors=True)
    shutil.copytree(paths.IMAGES / name, ctx)
    shutil.copy(paths.PILOT / "specfoundry_pilot" / "frame.py", ctx / "frame.py")
    for stray in ("build_args.py",):
        (ctx / stray).unlink(missing_ok=True)
    for dst, src in extra.items():
        shutil.copy(src, ctx / dst)
    return ctx


def _hash_dir(ctx: Path, args: dict) -> str:
    h = hashlib.sha256(json.dumps(args, sort_keys=True).encode())
    for p in sorted(ctx.rglob("*")):
        if p.is_file():
            h.update(p.name.encode())
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
    return h.hexdigest()[:12]


def build(name: str, extra: dict[str, Path], build_args: dict) -> str:
    ctx = _context(name, extra)
    tag = _hash_dir(ctx, build_args)
    ref = f"{paths.REGISTRY_HOST}/pilot-{name}:{tag}"
    args = ["docker", "build", "-q", "-t", ref]
    for k, v in build_args.items():
        args += ["--build-arg", f"{k}={v}"]
    print(f"== image pilot-{name}:{tag}", flush=True)
    _sh(*args, str(ctx))
    _sh("docker", "push", "-q", ref)
    digest = _sh("docker", "inspect", "--format", "{{range .RepoDigests}}{{println .}}{{end}}", ref)
    for line in digest.split():
        if line.startswith(f"{paths.REGISTRY_HOST}/pilot-{name}@sha256:"):
            return line
    raise RuntimeError(f"no registry digest for {ref}")


def _build_args(name: str) -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_args", paths.IMAGES / "build_args.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_args(name, paths.read_pins())


def build_all() -> dict:
    """`pilot up --local-build`: build from pilot/images/ (upstream inputs verified in the
    Dockerfiles) into the kind-local registry. Same build args as the GitHub workflow."""
    imgs = {name: build(name, {}, _build_args(name)) for name in ("worker", "tools", "egress")}
    paths.IMAGES_JSON.write_text(json.dumps(imgs, indent=2) + "\n")
    return imgs


def load() -> dict:
    return json.loads(paths.IMAGES_JSON.read_text())


# --- 003: digest-only references from pilot/images.lock (C-09, FR-005) -----------------

import re as _re  # noqa: E402

REF_RE = _re.compile(r"^[a-z0-9./:-]+@sha256:[0-9a-f]{64}$")
LOCK_KEYS = {"worker": "WORKER_IMAGE", "tools": "TOOLS_IMAGE", "egress": "EGRESS_IMAGE"}


class ImageRefError(Exception):
    pass


def validate_ref(ref: str) -> str:
    """Accept only name@sha256:<64 lowercase hex>; never a tag (also not tag@digest)."""
    if not ref or not REF_RE.match(ref):
        raise ImageRefError(f"not a digest reference: {ref!r}")
    name = ref.split("@", 1)[0]
    last = name.rsplit("/", 1)[-1]
    if ":" in last:  # a tag on the final path component (a registry port is allowed earlier)
        raise ImageRefError(f"tagged reference not allowed: {ref!r}")
    return ref


def load_pinned(lock: dict) -> dict:
    out = {}
    for short, key in LOCK_KEYS.items():
        try:
            out[short] = validate_ref(lock.get(key, ""))
        except ImageRefError as e:
            raise ImageRefError(f"{key} in pilot/images.lock: {e}") from None
    return out


def read_lock() -> dict:
    try:
        return paths.read_lock()
    except FileNotFoundError:
        raise ImageRefError(f"missing {paths.IMAGES_LOCK}") from None
