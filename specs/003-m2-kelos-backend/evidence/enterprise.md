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

## Published images (T024), 2026-11-13

Digests from `pilot/images.lock` on main (published by the pilot-images workflow, see
[ci.md](ci.md)):
- worker `ghcr.io/tosin2013/specfoundry-pilot-worker@sha256:bff0da27b9d34a68ca57d33068ae9d73b42d24993ee7ac42f63481a1df8fb3c6`
- tools `ghcr.io/tosin2013/specfoundry-pilot-tools@sha256:78c87dc4147a0e81525c3e821b274199a3a77489f6f04f34f0b1a6c4f97aa12b`
- egress `ghcr.io/tosin2013/specfoundry-pilot-egress@sha256:db46773a79c3c41129364bdf0399b76717af1e99a339943c833aaa28759a452a`

### Arbitrary-UID smoke test against the published digests

`WORKER=… TOOLS=… EGRESS=… pilot/images/smoke.sh` gave worker PASS (frame decoded), tools PASS
(grade pass), egress PASS (refused a non-allowlisted host): **3 of 3**.

### Real worker job, arbitrary UID, proxy-only egress (C1 and FR-009)

- **Network:** the worker ran on an **internal** Docker network with no route to the
  internet. Its only way out was the published egress image (as UID 1000123, read-only
  root), whose allowlist held only the operator's model host. The allowlist file and the
  credential copy lived outside the repo and were deleted afterwards.
- **Worker:** published worker image, `--user 1000123:0 --read-only --cap-drop ALL
  --security-opt no-new-privileges`, with `HTTPS_PROXY` set to the egress proxy, on fixture
  task A (full prompt).
- **Result:** harness exit 0, 228,949 tokens. Changed `specs/001-slugify/tasks.md`,
  `src/slugkit/__init__.py`, `src/slugkit/slug.py`, `tests/test_slug.py`.
- **Proxy:** 3 CONNECTs to the allowlisted model host, and **1 request refused** to a
  non-allowlisted host. A separate start-up run without a model made **no** outbound
  attempts, so the refused request came from the session itself (an agent tool call or a
  session-time OpenCode request). It was blocked as designed, and the job didn't need it.
  The host name was not captured here; pilot runs record it in each attempt's
  `proxy-denials.log` (T019).
- **Grading:** with the published tools image as UID 1000123, `--network none`: **pass**,
  G1–G5 all pass.

### Mirror by digest (US2 scenario 2)

The three images were copied with `docker buildx imagetools create` into a local
`registry:2` (the pinned digest from `pins.env`):

| Image | Source digest | Mirror digest |
|---|---|---|
| worker | `sha256:bff0da27b9d34a68ca57d33068ae9d73b42d24993ee7ac42f63481a1df8fb3c6` | identical |
| tools | `sha256:78c87dc4147a0e81525c3e821b274199a3a77489f6f04f34f0b1a6c4f97aa12b` | identical |
| egress | `sha256:db46773a79c3c41129364bdf0399b76717af1e99a339943c833aaa28759a452a` | identical |

Pulling by digest from the mirror works. An enterprise can mirror the images and keep the
same `@sha256:` values in `pilot/images.lock`, changing only the registry prefix.

**Result:** SC-003 met: 3 of 3 images run as an arbitrary UID with a read-only root fs,
including one real worker job that was then graded successfully.
