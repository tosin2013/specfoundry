"""Worker task prompt and the declared induction (research R6, FR-009c)."""
from __future__ import annotations

import hashlib

INDUCTION = "withheld-acceptance-section"
HEADING = "## Acceptance details"

PREAMBLE = """You are a coding agent working in a git repository (the current directory).
Implement the specification below completely, then mark every task in the task list as
done by changing `- [ ]` to `- [X]` in that tasks.md file.

Rules:
- Change only files under `src/slugkit/`, `tests/`, and the task list file named below.
- Use the Python standard library only. Do not install packages.
- Do not run git commands; the harness commits your work.
- When finished, stop.
"""


def _span(spec_md: str) -> tuple[int, int]:
    start = spec_md.find(HEADING)
    if start < 0:
        raise ValueError(f"induction requested but {HEADING!r} not found")
    nxt = spec_md.find("\n## ", start + len(HEADING))
    end = nxt + 1 if nxt >= 0 else len(spec_md)
    return start, end


def section_sha256(text: str) -> str:
    s, e = _span(text)
    return hashlib.sha256(text[s:e].encode()).hexdigest()


def build_prompt(spec_md: str, tasks_md: str, plan_md: str, induction: str | None,
                 tasks_path: str = "tasks.md") -> tuple[str, dict | None]:
    record = None
    if induction is not None:
        if induction != INDUCTION:
            raise ValueError(f"unknown induction {induction!r}")
        s, e = _span(spec_md)
        removed = spec_md[s:e]
        spec_md = spec_md[:s] + spec_md[e:]
        record = {"name": INDUCTION, "removed_heading": HEADING,
                  "removed_sha256": hashlib.sha256(removed.encode()).hexdigest(),
                  "removed_bytes": len(removed.encode())}
    text = (f"{PREAMBLE}\n# Specification\n\n{spec_md.strip()}\n\n# Plan\n\n{plan_md.strip()}\n\n"
            f"# Task list (`{tasks_path}`)\n\n{tasks_md.strip()}\n")
    return text, record
