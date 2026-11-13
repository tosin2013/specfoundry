# Enterprise readiness of the pilot images (003 US2)

## Local images (pre-publish), 2026-11-13

Images built locally from `pilot/images/` with the same build args as CI
(`pilot/images/build_args.py`); upstream OpenCode and spec verified by checksum in the
Dockerfiles.

### Arbitrary-UID smoke test (`pilot/images/smoke.sh`)

All runs: `--user 1000123:0 --read-only --cap-drop ALL --security-opt no-new-privileges`, with
only the pods' writable mounts as tmpfs.

| Image | Check | Result |
|---|---|---|
| worker | entrypoint runs its pipeline and emits a valid frame (no model config, so the harness errors) | PASS |
| tools | `grade.py` grades the reference solution, `--network none` | PASS (G1–G5 pass) |
| egress | tinyproxy starts and refuses a non-allowlisted host | PASS (`refused on filtered domain "blocked.invalid"`) |

### Real worker job under an arbitrary UID (analysis C1)

- Worker image as UID 1000123, read-only root, the operator's OpenCode config mounted read-only
  (a temporary copy outside the repo, deleted after the run), on fixture task A (full prompt).
- Result: harness exit 0, 178,622 tokens, changed `specs/001-slugify/tasks.md`,
  `src/slugkit/__init__.py`, `src/slugkit/slug.py`, `tests/test_slug.py`.
- Grading with the tools image as UID 1000123, `--network none`: **pass**, G1–G5 all pass.

## Published images

Pending T017: re-run the smoke test and the real-job check against the GHCR digests, plus
the proxy and mirror checks.
