# slugkit — Spec Roadmap

Throwaway fixture for the specfoundry M1 pilot. Two items: B depends on A.

Status legend (lifecycle): **undecided** · **needs-info** · **planned** ·
**specced** · **in-progress** · **implemented** · **verified** · **deferred** ·
**abandoned**.

---

## Planned Specs

### 001 — Slug function  [status: planned]

- **Description:** A `slugify` function for short, URL-safe identifiers.
- **Outcome:** `slugify(text)` meets every rule in its spec, including the acceptance details.
- **Scope (in):** `src/slugkit/slug.py`, its tests, and this spec's tasks.
- **Scope (out):** uniqueness handling (002).
- **Depends on:** none
- **Spec dir:** specs/001-slugify

### 002 — Unique slugs  [status: planned]

- **Description:** A `unique_slug` function that avoids collisions with existing slugs.
- **Outcome:** `unique_slug(text, existing)` returns a slug not in `existing`, built on `slugify`.
- **Scope (in):** `src/slugkit/unique.py`, its tests, and this spec's tasks.
- **Scope (out):** changing `slugify` behaviour.
- **Depends on:** 001
- **Spec dir:** specs/002-unique-slug
