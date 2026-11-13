"""`pilot publisher-token`: write publisher.env from a hidden prompt and verify the token's scope.

The token is read by bash (`read -s`) straight into the 0600 file and checked by a child
process that sources that file; it never enters the orchestrator's memory, logs or evidence.
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


def verify(cfg) -> dict:
    """Run check_token.py with the token sourced from publisher.env in the child only."""
    config.check_mode(cfg.publisher_env)
    canary = config.origin_repo()
    r = subprocess.run(["bash", "-c", 'set -a; . "$1"; set +a; exec python3 "$2" "$3" "$4"',
                        "_", str(cfg.publisher_env), str(CHECK), cfg.repo, canary or ""],
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


def run(cfg, check_only: bool = False) -> int:
    if not check_only:
        rc = write_from_prompt(cfg.publisher_env)
        if rc:
            return rc
    res = verify(cfg)
    report(res)
    return 0 if res.get("ok") else 1
