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

## Acceptance details

These rules are exact and are checked by the grader:

- The separator is the tilde character `~` (not `-`). Expose it as `SEPARATOR = "~"`.
- The maximum slug length is 37 characters. Expose it as `SLUG_MAX = 37`.
- When a slug is longer than `SLUG_MAX`, cut it to `SLUG_MAX` characters and then remove
  any trailing `~`.
- When the result would be empty, return the literal string `"n~a"`. Expose it as
  `EMPTY_SLUG = "n~a"`.

## Done when

- Every task in `tasks.md` is checked.
- `python3 -m pytest -q tests/` passes.
