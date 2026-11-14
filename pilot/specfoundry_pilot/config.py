"""Operator configuration (contracts/config.md).

Secrets are never read into Python memory. publisher.env is passed by path to
`kubectl create secret --from-env-file`; only its variable *names* are inspected. The worker's
OpenCode credentials are the files in `opencode/` (opencode.json + `<provider>_api_key`), passed
by path to `kubectl create secret --from-file`. Only opencode.json (which must hold no literal
key, only `{file:...}`/`{env:...}` references) is parsed.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

SCM_NAME_RE = re.compile(r"GITHUB|^GH_|GIT_.*TOKEN", re.I)
DEFAULTS = {
    "PILOT_FIXTURE_BRANCH": "main",
    "PILOT_SPEND_CAP_USD": "1.00",
    "PILOT_TOKEN_CAP": "2000000",
    "PILOT_PROVIDER_CAP_DECLARED": "false",
    "RETRY_LIMIT": "2",
}
REQUIRED = ["PILOT_FIXTURE_REPO", "PILOT_MODEL", "PILOT_MODEL_EGRESS_HOSTS"]


class ConfigError(Exception):
    """Configuration problem. `code` is the CLI exit code (2 = error, 3 = repo guard)."""

    def __init__(self, msg: str, code: int = 2):
        super().__init__(msg)
        self.code = code


@dataclass
class Config:
    values: dict
    config_dir: Path
    model_dir: Path
    publisher_env: Path
    extra: dict = field(default_factory=dict)

    def __getitem__(self, k):
        return self.values[k]

    @property
    def repo(self) -> str:
        return self.values["PILOT_FIXTURE_REPO"]

    @property
    def branch(self) -> str:
        return self.values["PILOT_FIXTURE_BRANCH"]

    @property
    def retry_limit(self) -> int:
        return int(self.values["RETRY_LIMIT"])

    @property
    def model_hosts(self) -> list[str]:
        return [h.strip() for h in self.values["PILOT_MODEL_EGRESS_HOSTS"].split(",") if h.strip()]

    @property
    def model_files(self) -> list[Path]:
        return model_files(self.model_dir)

    def public(self) -> dict:
        """Values safe for the committed evidence (config.json). The model provider's host
        name identifies the operator's provider, so only its hash is recorded."""
        import hashlib
        v = dict(self.values)
        if v.get("PILOT_MODEL_EGRESS_HOSTS"):
            v["PILOT_MODEL_EGRESS_HOSTS"] = ",".join(
                "sha256:" + hashlib.sha256(h.encode()).hexdigest()[:16] for h in self.model_hosts)
        return v


def config_dir() -> Path:
    return Path(os.environ.get("SPECFOUNDRY_CONFIG", str(Path.home() / ".config" / "specfoundry")))


GUIDE = "docs/operator-guide.md"
MISSING_HINTS = {
    "pilot.env": f"create it first: {GUIDE}, section 5 (Configure your model provider)",
    "publisher.env": "store the token first: pilot/pilot publisher-token",
    "opencode": f"create it first: {GUIDE}, section 5 (Configure your model provider)",
}


def missing_hint(path: Path) -> str:
    hint = MISSING_HINTS.get(path.name)
    return f"\n  {hint}" if hint else ""


def check_mode(path: Path) -> None:
    if not path.exists():
        raise ConfigError(f"missing config file: {path}{missing_hint(path)}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise ConfigError(f"{path} must be mode 0600 (is {oct(mode)})")


def parse_env(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #", 1)[0].strip().strip('"').strip("'")
        out[k.strip()] = v
    return out


def secret_names(path: Path) -> list[str]:
    """Variable names in a secret env file, without loading values into this process."""
    out = subprocess.run(
        ["bash", "-c", 'grep -v "^[[:space:]]*#" "$1" | grep "=" | cut -d= -f1', "_", str(path)],
        capture_output=True, text=True, check=False,
    ).stdout
    return [n.strip() for n in out.splitlines() if n.strip()]


REF_RE = re.compile(r"^\{(file|env):[^}]+\}$")
SECRET_FIELD_RE = re.compile(r"key|token|secret|password", re.I)


def model_files(d: Path) -> list[Path]:
    """opencode.json plus every `*_api_key` file (backups like *.bak.* are ignored)."""
    return [d / "opencode.json"] + sorted(p for p in d.glob("*_api_key") if p.is_file())


def check_model_dir(d: Path) -> None:
    if not d.is_dir():
        raise ConfigError(f"missing worker OpenCode config dir: {d}{missing_hint(d)}")
    if stat.S_IMODE(d.stat().st_mode) & 0o077:
        raise ConfigError(f"{d} must be mode 0700")
    files = model_files(d)
    for f in files:
        check_mode(f)
        if SCM_NAME_RE.search(f.name):
            raise ConfigError(f"{f.name}: SCM-like credential name; SCM credentials must never reach a worker")
    if len(files) < 2:
        raise ConfigError(f"{d} needs opencode.json and at least one <provider>_api_key file")
    import json
    try:
        doc = json.loads((d / "opencode.json").read_text())
    except ValueError as e:
        raise ConfigError(f"{d}/opencode.json is not valid JSON: {e}")

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and SECRET_FIELD_RE.search(k) and not REF_RE.match(v):
                    raise ConfigError(f"opencode.json {path}{k} must be a {{file:...}} reference, not a literal secret")
                walk(v, f"{path}{k}.")
        elif isinstance(o, list):
            for x in o:
                walk(x, path)
    walk(doc)


def origin_repo() -> str | None:
    r = subprocess.run(["git", "-C", str(paths.ROOT), "remote", "get-url", "origin"],
                       capture_output=True, text=True, check=False)
    url = r.stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else None


def repo_guard(repo: str, origin: str | None = None) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo or ""):
        raise ConfigError(f"PILOT_FIXTURE_REPO must be owner/name, got {repo!r}", 3)
    name = repo.split("/", 1)[1]
    if not name.endswith("-pilot-fixture"):
        raise ConfigError(f"repo guard: {repo} does not end in '-pilot-fixture'", 3)
    if origin is not None and repo.lower() == origin.lower():
        raise ConfigError(f"repo guard: {repo} is this repository's origin", 3)


def validate_values(values: dict) -> dict:
    v = dict(DEFAULTS)
    v.update({k: val for k, val in values.items() if val != ""})
    missing = [k for k in REQUIRED if not v.get(k)]
    if missing:
        raise ConfigError(f"pilot.env missing {missing}")
    try:
        rl = int(v["RETRY_LIMIT"])
    except ValueError:
        raise ConfigError("RETRY_LIMIT must be an integer")
    if rl < 0 or rl > 2:
        raise ConfigError("RETRY_LIMIT must be between 0 and 2 in M1")
    try:
        float(v["PILOT_SPEND_CAP_USD"]); int(v["PILOT_TOKEN_CAP"])
    except ValueError:
        raise ConfigError("PILOT_SPEND_CAP_USD / PILOT_TOKEN_CAP must be numeric")
    return v


def load(require_secrets: bool = True, guard: bool = True) -> Config:
    d = config_dir()
    pilot_env = d / "pilot.env"
    check_mode(pilot_env)
    values = validate_values(parse_env(pilot_env.read_text()))
    model_dir, publisher_env = d / "opencode", d / "publisher.env"
    if require_secrets:
        check_model_dir(model_dir)
        check_mode(publisher_env)
    if guard:
        repo_guard(values["PILOT_FIXTURE_REPO"], origin_repo())
    return Config(values=values, config_dir=d, model_dir=model_dir, publisher_env=publisher_env)
