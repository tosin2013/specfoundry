"""`pilot publisher-token`: write publisher.env from a hidden prompt and verify the token's scope.

The token is read by bash (`read -s`) straight into a 0600 staging file and checked by a child
process that sources that file; it never enters the orchestrator's memory, logs or evidence.
Only a token that passes the check replaces publisher.env; a failing one is deleted and any
previous token is kept (validation finding F3).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import config, paths

CHECK = paths.IMAGES / "tools" / "check_token.py"


def write_from_prompt(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    print("Paste the fine-grained token for the fixture repo (input hidden):")
    r = subprocess.run(["bash", "-c",
                        'umask 077; IFS= read -rs T </dev/tty || exit 3; echo >/dev/tty; [ -n "$T" ] || exit 4; '
                        'printf "PILOT_SCM_TOKEN=%s\\n" "$T" > "$1"; unset T', "_", str(path)])
    if r.returncode != 0:
        print("no token written")
        return 2
    path.chmod(0o600)
    return 0


def verify(cfg, env_file: Path | None = None) -> dict:
    """Run check_token.py with the token sourced from env_file (default publisher.env) in the child only."""
    env_file = env_file or cfg.publisher_env
    config.check_mode(env_file)
    canary = config.origin_repo()
    r = subprocess.run(["bash", "-c", 'set -a; . "$1"; set +a; exec python3 "$2" "$3" "$4"',
                        "_", str(env_file), str(CHECK), cfg.repo, canary or ""],
                       capture_output=True, text=True, timeout=90)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {"ok": False, "problems": [f"token check failed to run: {(r.stderr or '').strip()[-300:]}"]}


def report(res: dict) -> None:
    print(f"publisher token: {'OK' if res.get('ok') else 'NOT OK'}")
    for k in ("login", "repo", "repo_push", "canary", "canary_push", "expires"):
        if k in res:
            print(f"  {k}: {res[k]}")
    for p in res.get("problems", []):
        print(f"  problem: {p}")


def staging_path(cfg) -> Path:
    return cfg.publisher_env.with_name(cfg.publisher_env.name + ".new")


def run(cfg, check_only: bool = False) -> int:
    if check_only:
        res = verify(cfg)
        report(res)
        return 0 if res.get("ok") else 1
    new = staging_path(cfg)
    try:
        rc = write_from_prompt(new)
        if rc:
            return rc
        res = verify(cfg, new)
        report(res)
        if not res.get("ok"):
            kept = "your previous token is unchanged" if cfg.publisher_env.exists() else "no token stored"
            print(f"  not saved: {kept}. Fix the token's scope and run this again.")
            return 1
        new.replace(cfg.publisher_env)
        print(f"  saved: {cfg.publisher_env}")
        return 0
    finally:
        new.unlink(missing_ok=True)
