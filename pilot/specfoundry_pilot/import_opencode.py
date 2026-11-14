"""`pilot import-opencode`: reuse an existing host OpenCode setup as the worker's config.

Copies only what the worker needs: the provider of the chosen model, and the key files that
provider references. Key files are copied with `install -m 600` and never read into this
process. The model host is never printed; it is written to pilot.env (a 0600 file) or
compared with the value already there.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from . import config
from .config import ConfigError

KEEP_TOP = ("$schema", "providers", "model")
FILE_REF = re.compile(r"^\{file:(.+)\}$")
ENV_REF = re.compile(r"^\{env:(.+)\}$")
WORKER_DIR = "~/.config/opencode/"


def _walk_secrets(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and config.SECRET_FIELD_RE.search(k):
                yield f"{path}{k}", v
            yield from _walk_secrets(v, f"{path}{k}.")
    elif isinstance(o, list):
        for x in o:
            yield from _walk_secrets(x, path)


def plan(src: Path, model: str | None = None) -> dict:
    """Validate the host config and decide what to copy. Raises ConfigError with a fix."""
    cfg_file = src / "opencode.json"
    if not cfg_file.exists():
        extra = " (opencode.jsonc is not supported: save it as plain JSON)" if (src / "opencode.jsonc").exists() else ""
        raise ConfigError(f"no OpenCode config at {cfg_file}{extra}")
    try:
        doc = json.loads(cfg_file.read_text())
    except ValueError as e:
        raise ConfigError(f"{cfg_file} is not valid JSON: {e}")
    model = model or doc.get("model")
    if not model or "/" not in model:
        raise ConfigError("no default model: set \"model\": \"<provider>/<model>\" in opencode.json, or pass --model")
    prov_name, model_id = model.split("/", 1)
    prov = (doc.get("providers") or {}).get(prov_name)
    if not isinstance(prov, dict):
        raise ConfigError(f"provider {prov_name!r} (from model {model!r}) is not defined under \"providers\"")
    if model_id not in (prov.get("models") or {}):
        raise ConfigError(f"model {model_id!r} is not listed under providers.{prov_name}.models")
    base_url = (prov.get("settings") or {}).get("baseURL") or ""
    host = urlparse(base_url).hostname
    if not host:
        raise ConfigError(f"providers.{prov_name}.settings.baseURL must be a full https:// URL")
    keys = []
    for where, val in _walk_secrets(prov, f"providers.{prov_name}."):
        if ENV_REF.match(val):
            raise ConfigError(f"{where} uses an {{env:...}} reference; the worker can't see your environment. "
                              f"Put the key in {WORKER_DIR}{prov_name}_api_key and use "
                              f"\"{{file:{WORKER_DIR}{prov_name}_api_key}}\"")
        m = FILE_REF.match(val)
        if not m:
            raise ConfigError(f"{where} holds a literal secret; move it to {WORKER_DIR}{prov_name}_api_key "
                              f"and use \"{{file:{WORKER_DIR}{prov_name}_api_key}}\" (value not shown)")
        ref = m.group(1)
        name = Path(ref).name
        if not ref.startswith(WORKER_DIR) or "/" in ref[len(WORKER_DIR):] or not name.endswith("_api_key"):
            raise ConfigError(f"{where} must reference {WORKER_DIR}<name>_api_key (got {ref!r}); "
                              "the worker mounts only those files")
        if not (src / name).is_file():
            raise ConfigError(f"{where} references {name}, which is missing from {src}")
        keys.append(name)
    if not keys:
        raise ConfigError(f"providers.{prov_name} has no apiKey; add \"apiKey\": \"{{file:{WORKER_DIR}{prov_name}_api_key}}\"")
    others = sorted(k for k in (doc.get("providers") or {}) if k != prov_name)
    dropped = sorted(k for k in doc if k not in KEEP_TOP)
    out = {k: doc[k] for k in ("$schema",) if k in doc}
    out.update({"providers": {prov_name: prov}, "model": model})
    return {"doc": out, "keys": sorted(set(keys)), "model": model, "host": host,
            "dropped_providers": others, "dropped_settings": dropped}


def write_pilot_env(path: Path, model: str, host: str, fixture_repo: str | None) -> None:
    subprocess.run(["install", "-m", "600", "/dev/null", str(path)], check=True)
    path.write_text(
        f"PILOT_FIXTURE_REPO={fixture_repo or ''}\n"
        "PILOT_FIXTURE_BRANCH=main\n"
        f"PILOT_MODEL={model}\n"
        f"PILOT_MODEL_EGRESS_HOSTS={host}\n"
        "PILOT_SPEND_CAP_USD=1.00\n"
        "PILOT_TOKEN_CAP=2000000\n"
        "PILOT_PROVIDER_CAP_DECLARED=false\n")


def run(src: Path, model: str | None = None, fixture_repo: str | None = None, force: bool = False) -> int:
    p = plan(src, model)
    d = config.config_dir()
    dest = d / "opencode"
    if (dest / "opencode.json").exists() and not force:
        raise ConfigError(f"{dest} already has an opencode.json; pass --force to replace it")
    if fixture_repo:
        config.repo_guard(fixture_repo, config.origin_repo())
    subprocess.run(["install", "-d", "-m", "700", str(d), str(dest)], check=True)
    for name in p["keys"]:
        subprocess.run(["install", "-m", "600", str(src / name), str(dest / name)], check=True)
    target = dest / "opencode.json"
    subprocess.run(["install", "-m", "600", "/dev/null", str(target)], check=True)
    target.write_text(json.dumps(p["doc"], indent=2) + "\n")
    config.check_model_dir(dest)

    print(f"imported OpenCode config: {src} -> {dest}")
    print(f"  model: {p['model']}")
    print(f"  key files: {', '.join(p['keys'])}")
    if p["dropped_providers"]:
        print(f"  left out other providers: {', '.join(p['dropped_providers'])}")
    if p["dropped_settings"]:
        print(f"  left out settings the worker can't use: {', '.join(p['dropped_settings'])}")

    pilot_env = d / "pilot.env"
    if not pilot_env.exists():
        write_pilot_env(pilot_env, p["model"], p["host"], fixture_repo)
        print(f"wrote {pilot_env} (model, its egress host, default caps)")
        if not fixture_repo:
            print("  next: set PILOT_FIXTURE_REPO=<you>/<you>-pilot-fixture in it")
        return 0
    values = config.parse_env(pilot_env.read_text())
    hosts = [h.strip() for h in values.get("PILOT_MODEL_EGRESS_HOSTS", "").split(",") if h.strip()]
    ok = True
    if values.get("PILOT_MODEL") != p["model"]:
        print(f"  pilot.env: set PILOT_MODEL={p['model']} (it is {values.get('PILOT_MODEL') or 'unset'})")
        ok = False
    if p["host"] not in hosts:
        print("  pilot.env: PILOT_MODEL_EGRESS_HOSTS doesn't include your provider's host; "
              "set it to the host part of the provider's baseURL")
        ok = False
    print(f"pilot.env: {'matches' if ok else 'needs the changes above'} ({pilot_env} left unchanged)")
    return 0
