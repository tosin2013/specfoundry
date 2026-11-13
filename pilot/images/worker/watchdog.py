"""Spend-cap watchdog for one OpenCode attempt (research R2).

    opencode run --format json ... | watchdog.py <harness_pid>

Tees every event line to /tmp/harness.jsonl, sums step_finish cost and tokens (keyed by
part id), and SIGTERMs the harness when the cap is reached. Writes /tmp/spend.json at EOF.
Cap modes: "cost" while any non-zero cost has been reported; otherwise "token-fallback".
"""
from __future__ import annotations

import json
import os
import signal
import sys


def tokens_of(t) -> int:
    if not isinstance(t, dict):
        return 0
    return int(t.get("input") or 0) + int(t.get("output") or 0) + int(t.get("reasoning") or 0)


class Meter:
    def __init__(self, cap_usd: float, token_cap: int):
        self.cap_usd, self.token_cap = cap_usd, token_cap
        self.seen: dict[str, tuple[float, int]] = {}
        self.stopped_by_cap = False

    def feed(self, line: str) -> bool:
        """Account one event line; return True if the cap is now exceeded."""
        try:
            e = json.loads(line)
        except ValueError:
            return False
        if not isinstance(e, dict) or e.get("type") != "step_finish":
            return False
        p = e.get("part") or {}
        key = str(p.get("id") or len(self.seen))
        self.seen[key] = (float(p.get("cost") or 0.0), tokens_of(p.get("tokens")))
        return self.exceeded()

    @property
    def cost(self) -> float:
        return round(sum(c for c, _ in self.seen.values()), 6)

    @property
    def tokens(self) -> int:
        return sum(t for _, t in self.seen.values())

    @property
    def mode(self) -> str:
        return "cost" if self.cost > 0 else "token-fallback"

    def exceeded(self) -> bool:
        return self.cost >= self.cap_usd if self.mode == "cost" else self.tokens >= self.token_cap

    def report(self) -> dict:
        return {"cap_usd": self.cap_usd, "token_cap": self.token_cap, "cap_mode": self.mode,
                "cost_usd": self.cost, "tokens": self.tokens, "stopped_by_cap": self.stopped_by_cap}


def main(argv) -> int:
    pid = int(argv[1]) if len(argv) > 1 else 0
    m = Meter(float(os.environ.get("PILOT_SPEND_CAP_USD", "1.00")), int(os.environ.get("PILOT_TOKEN_CAP", "2000000")))
    with open("/tmp/harness.jsonl", "a") as log:
        for line in sys.stdin:
            log.write(line)
            log.flush()
            if m.feed(line) and not m.stopped_by_cap:
                m.stopped_by_cap = True
                if pid:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
    with open("/tmp/spend.json", "w") as f:
        json.dump(m.report(), f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
