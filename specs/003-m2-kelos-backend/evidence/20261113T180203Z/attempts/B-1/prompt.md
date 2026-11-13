You are a coding agent working in a git repository (the current directory).
Implement the specification below completely, then mark every task in the task list as
done by changing `- [ ]` to `- [X]` in that tasks.md file.

Rules:
- Change only files under `src/slugkit/`, `tests/`, and the task list file named below.
- Use the Python standard library only. Do not install packages.
- Do not run git commands; the harness commits your work.
- When finished, stop.

# Specification

# Spec 002: Unique slugs

## Goal

Provide `unique_slug(text: str, existing: set[str]) -> str` in `src/slugkit/unique.py`,
exported from `slugkit` (`from slugkit import unique_slug`). It must reuse `slugify`
and the constants from spec 001 rather than re-implementing them.

## Behaviour

1. Compute `base = slugify(text)`.
2. If `base` is not in `existing`, return it.
3. Otherwise try suffixes until a free slug is found.
4. Never modify `existing`.

## Acceptance details

These rules are exact and are checked by the grader:

- Suffixes are `SEPARATOR + str(n)` for n = 2, 3, 4, … (so `abc~2`, `abc~3`).
- The full result, including the suffix, must be at most `SLUG_MAX` characters: cut the
  base so that `len(base) + len(suffix) <= SLUG_MAX`, and remove any trailing `~` from the
  cut base before adding the suffix.
- If `base` is `EMPTY_SLUG` and it is taken, the suffix rules above still apply
  (`n~a~2`).

## Done when

- Every task in `tasks.md` is checked.
- `python3 -m pytest -q tests/` passes.

# Plan

# Plan

- Language: Python 3 standard library only.
- Code lives under `src/slugkit/`; tests under `tests/` (pytest).
- Follow `spec.md` exactly, including the "Acceptance details" section.

# Task list (`specs/002-unique-slug/tasks.md`)

# Tasks: 002 Unique slugs

- [ ] T001 Implement `unique_slug` in `src/slugkit/unique.py` using `slugify` and the 001 constants
- [ ] T002 Export `unique_slug` from `src/slugkit/__init__.py`
- [ ] T003 Add tests for every rule in the spec to `tests/test_unique.py`
