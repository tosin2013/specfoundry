You are a coding agent working in a git repository (the current directory).
Implement the specification below completely, then mark every task in the task list as
done by changing `- [ ]` to `- [X]` in that tasks.md file.

Rules:
- Change only files under `src/slugkit/`, `tests/`, and the task list file named below.
- Use the Python standard library only. Do not install packages.
- Do not run git commands; the harness commits your work.
- When finished, stop.

# Specification

# Spec 001: Slug function

## Goal

Provide `slugify(text: str) -> str` in `src/slugkit/slug.py`, exported from
`slugkit` (`from slugkit import slugify`). The module must also define the constants
named below.

## Behaviour

1. Lowercase the input.
2. Treat every run of characters that are not ASCII letters or digits as one separator.
3. Remove separators at the start and end.
4. Use only the Python standard library.

## Done when

- Every task in `tasks.md` is checked.
- `python3 -m pytest -q tests/` passes.

# Plan

# Plan

- Language: Python 3 standard library only.
- Code lives under `src/slugkit/`; tests under `tests/` (pytest).
- Follow `spec.md` exactly, including the "Acceptance details" section.

# Task list (`specs/001-slugify/tasks.md`)

# Tasks: 001 Slug function

- [ ] T001 Implement `slugify`, `SEPARATOR`, `SLUG_MAX` and `EMPTY_SLUG` in `src/slugkit/slug.py`
- [ ] T002 Export `slugify` from `src/slugkit/__init__.py`
- [ ] T003 Add tests for every rule in the spec to `tests/test_slug.py`
