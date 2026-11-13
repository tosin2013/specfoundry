#!/usr/bin/env python3
"""Docs check (006, contracts/docs-check.md). Stdlib only.

    python3 pilot/tools/docs_check.py [FILE ...]   # default: docs/*.md README.md pilot/README.md

D1  every `pilot/pilot <sub> [--flags]` in an sh/bash/shell code block exists in the CLI's --help
D2  repo paths exist: relative Markdown links, and inline-code tokens that start with a
    top-level repo entry (pilot/, specs/, docs/, …). Domains, owner/repo slugs, ~ paths,
    <placeholders>, globs and URLs are never treated as paths (analysis H1)
D3  quoted versions of kind, kubectl, Calico, spec and OpenCode match pilot/pins.env
D4  nothing matches the evidence redaction patterns (token-like strings)

Exit 0 = clean, 1 = failures (all listed), 2 = usage/internal error.
"""
from __future__ import annotations

import functools
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pilot"))
from specfoundry_pilot.audit import PATTERNS  # noqa: E402

TOP_LEVEL = ("pilot/", "specs/", "docs/", "test/", ".github/", ".specify/")
TOP_FILES = {"README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "LICENSE"}
SHELL_LANGS = {"sh", "bash", "shell", "console"}
FENCE = re.compile(r"^\s*```(\S*)")
LINK = re.compile(r"\]\(([^)\s]+)\)")
INLINE = re.compile(r"`([^`\n]+)`")
SECRET = re.compile(PATTERNS)


def read_pins() -> dict:
    out = {}
    for line in (ROOT / "pilot/pins.env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def _help(*args) -> str:
    r = subprocess.run([str(ROOT / "pilot/pilot"), *args, "--help"], capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr


@functools.lru_cache(maxsize=None)
def subcommands() -> frozenset:
    m = re.search(r"\{([a-z,-]+)\}", _help())
    return frozenset(m.group(1).split(",")) if m else frozenset()


@functools.lru_cache(maxsize=None)
def flags(sub: str) -> frozenset:
    return frozenset(re.findall(r"(--[a-z][a-z-]*)", _help(sub))) | {"--help"}


def check_command(line: str) -> list[str]:
    errs = []
    for m in re.finditer(r"pilot/pilot(?:\s+([^\s;&|#]+))?((?:\s+[^\s;&|#]+)*)", line):
        sub, rest = m.group(1), m.group(2) or ""
        if not sub or sub.startswith("<") or sub == "--help":
            continue
        if sub not in subcommands():
            errs.append(f"unknown subcommand {sub!r}")
            continue
        for tok in rest.split():
            if tok.startswith("--"):
                flag = tok.split("=", 1)[0]
                if flag not in flags(sub):
                    errs.append(f"unknown flag {flag} for {sub!r}")
    return errs


def looks_like_repo_path(tok: str) -> bool:
    tok = tok.strip().rstrip(".,;:)")
    if not tok or any(c in tok for c in " <>*{}$") or "://" in tok or tok.startswith(("~", "/", "-")):
        return False
    return tok.startswith(TOP_LEVEL) or tok in TOP_FILES


def path_exists(tok: str, doc: Path) -> bool:
    tok = tok.strip().rstrip(".,;:)").split("#", 1)[0]
    if not tok:
        return True
    for base in (doc.parent, ROOT):
        if (base / tok).exists():
            return True
    return False


VERSION_RULES = [
    (re.compile(r"\bkind v(\d+\.\d+\.\d+)"), "KIND_VERSION", "kind"),
    (re.compile(r"\bkubectl v(\d+\.\d+\.\d+)"), "KUBECTL_VERSION", "kubectl"),
    (re.compile(r"\bCalico v(\d+\.\d+\.\d+)", re.I), "CALICO_VERSION", "Calico"),
    (re.compile(r"\b(?:spec|spec-status)[ _]v?(\d+\.\d+\.\d+)"), "SPEC_VERSION", "spec"),
    (re.compile(r"\bOpenCode v?(\d+\.\d+\.\d+)", re.I), "OPENCODE_VERSION", "OpenCode"),
]


def check_file(path: Path, pins: dict) -> list[str]:
    errs = []
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    in_block, lang = False, ""
    for n, line in enumerate(path.read_text().splitlines(), 1):
        where = f"{rel}:{n}:"
        f = FENCE.match(line)
        if f:
            in_block, lang = (not in_block), (f.group(1).lower() if not in_block else "")
            continue
        if SECRET.search(line):
            errs.append(f"{where} token-like string (D4)")
        for rx, key, name in VERSION_RULES:
            for m in rx.finditer(line):
                want = pins.get(key, "").lstrip("v")
                if want and m.group(1) != want:
                    errs.append(f"{where} {name} {m.group(1)} != pins {want} (D3)")
        if in_block:
            if lang in SHELL_LANGS and "pilot/pilot" in line:
                errs += [f"{where} {e} (D1)" for e in check_command(line)]
            continue
        for m in LINK.finditer(line):
            target = m.group(1)
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if not path_exists(target, path):
                errs.append(f"{where} missing link target {target} (D2)")
        for m in INLINE.finditer(line):
            tok = m.group(1)
            if looks_like_repo_path(tok) and not path_exists(tok, path):
                errs.append(f"{where} missing path {tok} (D2)")
            elif "pilot/pilot" in tok:
                errs += [f"{where} {e} (D1)" for e in check_command(tok)]
    return errs


def default_files() -> list[Path]:
    return sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md", ROOT / "pilot/README.md"]


def check_files(files) -> list[str]:
    pins = read_pins()
    errs = []
    for f in files:
        errs += check_file(Path(f).resolve(), pins)
    return errs


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        files = [Path(a) for a in argv] or default_files()
        missing = [str(f) for f in files if not Path(f).exists()]
        if missing:
            print(f"docs_check: no such file: {missing}", file=sys.stderr)
            return 2
        errs = check_files(files)
    except Exception as e:  # noqa: BLE001
        print(f"docs_check: internal error: {e}", file=sys.stderr)
        return 2
    for e in errs:
        print(e)
    print(f"docs_check: {len(errs)} problem(s) in {len(files)} file(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
