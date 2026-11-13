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
