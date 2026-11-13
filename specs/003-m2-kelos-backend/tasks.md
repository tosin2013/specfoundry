---
description: "Task list for 003 — M2 hardened images and Kelos competitive review"
---

# Tasks: M2 hardened images and Kelos competitive review

**Input**: Design documents from `specs/003-m2-kelos-backend/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) (R1–R8),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The plan's Testing section requires unit tests for pins validation,
the Calico hash check and image-source selection, plus a full plain-Jobs pilot run on the
GitHub-built images (SC-002).

**Organization**:
- US1 = GitHub-built images pulled by digest (P1, MVP)
- US2 = enterprise-ready images (P2)
- US3 = factual Kelos competitive review (P2)

**Conventions**:
- Python 3.12 stdlib only, subprocess for external tools (as 002).
- Every `*_IMAGE` value must match `^[a-z0-9./-]+@sha256:[0-9a-f]{64}$` (data-model.md).
- No Kelos component is installed, adapted or forked anywhere (FR-014).
- Secrets never enter images, the workflow, logs or evidence.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Record upstream inputs in `pilot/pins.env`:
  - `OPENCODE_RELEASE=anomalyco/opencode@v2.2.7`
  - `OPENCODE_ASSET=opencode-linux-x64.tar.gz`
  - `OPENCODE_ASSET_SHA256=` (the value from that release's `SHA256SUMS`, fetched with `gh release download v2.2.7 -R anomalyco/opencode -p SHA256SUMS`)
  - `SPEC_RELEASE=tosin2013/spec-status@v0.2.0`
  - `SPEC_ASSET=spec_0.2.0_linux_amd64.tar.gz`
  - `SPEC_ASSET_SHA256=` (from `spec_0.2.0_checksums.txt`)
  - Keep the existing `SPEC_SHA256` (binary) and `OPENCODE_SHA256` (002 host binary, for comparison only).
- [X] T002 [P] Record `CALICO_SHA256` in `pilot/pins.env`: download `https://raw.githubusercontent.com/projectcalico/calico/v3.29.3/manifests/calico.yaml`, compute its sha256, and confirm it matches the hash recorded in `specs/002-m1-gated-pilot/evidence/20261113T030655Z/versions.txt` (`calico: v3.29.3 sha256=…`). If they differ, stop and report; don't pick one.
- [X] T003 [P] Create `pilot/images.lock` (env format) with `IMAGE_REGISTRY=ghcr.io/tosin2013`, `WORKER_IMAGE=`, `TOOLS_IMAGE=`, `EGRESS_IMAGE=` and a header comment: "written only by the pilot-images workflow's digest PR (C-09); never a workflow trigger". `pilot/images.lock` holds only the three image digests and is **never a workflow trigger**. The workflow's inputs (`pilot/pins.env`, `pilot/images/**`, `frame.py`) are never edited by the bot. So merging a digest PR cannot start another build (no build → PR → merge loop; analysis F1). Add `paths.IMAGES_LOCK` and `paths.read_lock()` (same parser as `read_pins()`) in `pilot/specfoundry_pilot/paths.py`.

---

## Phase 2: Foundational

- [X] T004 Write `pilot/tests/test_pins.py`:
  - `paths.read_pins()` keeps values verbatim;
  - a new `images.validate_ref(ref)` accepts `ghcr.io/tosin2013/specfoundry-pilot-worker@sha256:<64 hex>`;
  - it rejects `…:latest`, `…:sha-abc`, an empty string, uppercase hex, and a digest with 63 hex characters;
  - `images.load_pinned(lock)` (the parsed `pilot/images.lock`) returns `{worker, tools, egress}` when all three are valid, and raises `ImageRefError` naming the bad key otherwise;
  - `paths.read_lock()` reads `pilot/images.lock`, and a missing file raises `ImageRefError`.
- [X] T005 Implement `validate_ref()`, `ImageRefError` and `load_pinned(lock: dict) -> dict` in `pilot/specfoundry_pilot/images.py`, with the regex `^[a-z0-9./-]+@sha256:[0-9a-f]{64}$`. Keep `build_all()` unchanged as the local-build path.

**Checkpoint**: `python3 -m unittest discover -s pilot/tests -t pilot` passes (all 69 existing tests plus the new ones).

---

## Phase 3: User Story 1 — GitHub-built images pulled by digest (Priority: P1) 🎯 MVP

**Goal**:
- GitHub Actions builds the worker (upstream OpenCode, verified), tools (upstream spec, verified) and egress images.
- It pushes them as public GHCR packages and PRs the digests into `pilot/images.lock` (never a trigger, so no loop).
- `pilot up` pulls by digest and checks the Calico hash.
- A pilot run on these images passes its audit.

**Independent Test**: quickstart.md sections 1, 3 and 4. The workflow run is green; the digest PR merges; `pilot up` uses no local registry; the negative checks exit 2; a full pilot run gives audit 11/11 with `image_source: pinned`.

### Tests for User Story 1 ⚠️ (write first)

- [X] T006 [P] [US1] Write `pilot/tests/test_calico_hash.py` for a new `cluster.verify_calico(path, expected_sha256)`: a matching file passes; a mismatched file raises `RuntimeError` mentioning both hashes; an empty expected value raises.
- [X] T007 [P] [US1] Write `pilot/tests/test_image_source.py`:
  - `cluster.up()` with `local_build=False` calls `images.load_pinned` and never `images.build_all`, nor starts the registry;
  - with `local_build=True`, it calls `build_all` and starts the registry;
  - `evidence.write_versions` writes `image_source: pinned|local-build` plus the three refs (use `unittest.mock` to stub `sh`, `k8s` and `images`).

### Implementation for User Story 1

- [X] T008 [US1] Change `pilot/images/worker/Dockerfile`:
  - replace `COPY opencode` with a build stage that downloads `${OPENCODE_ASSET}` and `SHA256SUMS` from `https://github.com/${OPENCODE_RELEASE_REPO}/releases/download/${OPENCODE_VERSION_TAG}/`;
  - verify with `grep " ${OPENCODE_ASSET}$" SHA256SUMS | sha256sum -c -` **and** `echo "${OPENCODE_ASSET_SHA256}  ${OPENCODE_ASSET}" | sha256sum -c -`;
  - extract, locate the `opencode` binary inside the tarball (verify the layout), and copy it to `/usr/local/bin/opencode`;
  - fail the build on any mismatch;
  - keep apt pins, uid 10001, no sudo (`! command -v sudo`), and the `OPENCODE_DISABLE_*` env.
- [X] T009 [P] [US1] Change `pilot/images/tools/Dockerfile`: replace `COPY spec` with a download of `${SPEC_ASSET}` and `spec_0.2.0_checksums.txt` from the `tosin2013/spec-status` v0.2.0 release. Verify both the checksums-file entry and `SPEC_ASSET_SHA256`, extract `spec`, then verify the extracted binary against `SPEC_SHA256`.
- [X] T010 [US1] Create `.github/workflows/pilot-images.yml` per contracts/image-workflow.md:
  - **Triggers:** `push` to `main` and `pull_request` on `pilot/images/**`, `pilot/specfoundry_pilot/frame.py`, `pilot/pins.env`, with `pilot/images.lock` excluded by a negated path filter (`!pilot/images.lock`; GitHub forbids `paths` plus `paths-ignore`); plus `workflow_dispatch`. The bot only ever changes `pilot/images.lock`, so its PRs never trigger a build (F1).
  - **Loop guard (defence in depth):** the build job also skips when `github.head_ref` or the pushed branch starts with `pilot-images/`, or when the head commit message contains `[pilot-images]`.
  - **Matrix:** `target: [{registry: ghcr.io, namespace: tosin2013, variant: default}]` × `image: [worker, tools, egress]`.
  - **Build:** a step reads build args from `pilot/pins.env`, copies `frame.py` into each context, and runs `docker/build-push-action` pinned to a commit SHA, with `push: ${{ github.event_name != 'pull_request' }}`.
  - **Names:** `<registry>/<namespace>/specfoundry-pilot-<image>:sha-<short-commit>`.
  - **Permissions:** `contents: read` (the PR job gets `contents: write`, `pull-requests: write`), `packages: write`.
  - **Pinning:** all third-party actions pinned by full commit SHA.
  - **Provenance and SBOM (analysis D1):** set `provenance: mode=max` and `sbom: true` on the build step for pushed images, so each image carries a build-provenance attestation and an SPDX SBOM; record the attestation digests in `image-digests.json`.
- [X] T011 [US1] Add the digest-PR job to `.github/workflows/pilot-images.yml`. It runs only on `push`/`workflow_dispatch` after all matrix builds:
  - collect the digests into `image-digests.json` (data-model.md shape) and upload it as an artifact;
  - rewrite `WORKER_IMAGE`, `TOOLS_IMAGE` and `EGRESS_IMAGE` in `pilot/images.lock` (and nothing else) to `name@sha256:…`, with the commit message `chore(images): update digests [pilot-images]`;
  - open or update a PR from branch `pilot-images/<short-commit>` with `gh pr create` and the workflow's `GITHUB_TOKEN`;
  - never push to `main`;
  - skip the PR if the digests are unchanged;
  - fail the job if the diff touches any file other than `pilot/images.lock`.
- [X] T012 [US1] Implement `verify_calico()` in `pilot/specfoundry_pilot/cluster.py` and call it in `up_cluster()` before `kubectl apply`, using `CALICO_SHA256` from pins (FR-007).
- [X] T013 [US1] Change `cluster.up(cfg, cluster_only=False, local_build=False)` in `pilot/specfoundry_pilot/cluster.py`:
  - default path: `images.load_pinned(paths.read_lock())`, with no local registry container and no `containerdConfigPatches` dependency (it stays harmless);
  - `local_build=True`: today's registry plus `images.build_all()`;
  - pass `image_source` through to `paths.UP_OK` json and `images.json`.
- [X] T014 [US1] Add `--local-build` to `pilot up` in `pilot/specfoundry_pilot/cli.py`, and make `evidence.write_versions()` in `pilot/specfoundry_pilot/evidence.py` write `image_source:` plus the three image refs. The pipeline reads `image_source` from `images.json`.
- [X] T015 [US1] Make `pilot up` fail closed when an image can't be pulled: after `infra.apply_all`, wait for the egress proxy rollouts and the control and stand-in pods (they use the tools and egress digests). On `ImagePullBackOff`/`ErrImagePull` within 180 s, exit 2 with the image ref in the message; don't fall back to a local build (spec edge case).
- [X] T016 [US1] Commit Phase 1–3 changes on the feature branch, push it, open a PR, and confirm the `pull_request` workflow run builds all three images **without pushing** (SC-005). Record the run URL in `specs/003-m2-kelos-backend/evidence/ci.md`.
- [X] T017 [US1] After that PR is merged by the owner, confirm the `push` run publishes the three packages. Set the GHCR packages' visibility to **public** (package settings, a one-time owner action if the API can't). Confirm the bot's digest PR is opened and changes only `pilot/images.lock`; the owner merges it. Confirm that merge triggers **no** new `pilot-images` workflow run (F1). Record the package URLs, digests and the no-retrigger observation in `specs/003-m2-kelos-backend/evidence/ci.md`. Also confirm each pushed image has a provenance attestation and an SBOM (`docker buildx imagetools inspect <ref> --format '{{json .Provenance}}'` and `'{{json .SBOM}}'`), and record both in `evidence/ci.md` (D1).
- [X] T018 [US1] Compare the upstream OpenCode binary's sha256 (from the built worker image) with the 002 host binary (`OPENCODE_SHA256`), and record "identical" or "differs" in `specs/003-m2-kelos-backend/research.md` R4.
- [X] T019 [US1] Run the validation pilot (quickstart.md §3–§4): `pilot up` (expect no registry container, Calico hash OK), the two negative checks (a wrong `CALICO_SHA256` in `pins.env`, a tag-only `WORKER_IMAGE` in `images.lock` → exit 2), then `reset-fixture`, `run`, merge, `resume`, `down`, `audit`. Commit `specs/003-m2-kelos-backend/evidence/<run-id>/` (expect audit 11/11, `image_source: pinned`).

**Checkpoint**: SC-001, SC-002, SC-004, SC-005 met.

---

## Phase 4: User Story 2 — Enterprise-ready images (Priority: P2)

**Goal**: Each image runs under an arbitrary UID with a read-only root filesystem, honours proxies, and can be mirrored by digest. The worker image also offers a Kelos-compatible entrypoint.

**Independent Test**: quickstart.md §2. Each image completes its job under `--user 1000123:0 --read-only`, and a pilot referencing a mirrored copy behaves the same.

- [X] T020 [P] [US2] Make `pilot/images/worker/Dockerfile` arbitrary-UID friendly: `chgrp -R 0 /home/worker /work && chmod -R g=u /home/worker /work`, `HOME=/home/worker`. Check that `pilot/images/worker/entrypoint.sh` uses only `$HOME`, `/tmp` and `/work`, with no username or UID assumptions.
- [X] T021 [P] [US2] Make `pilot/images/tools/Dockerfile` and `pilot/images/egress/Dockerfile` arbitrary-UID friendly: group-0 writable home, `/tmp` only for scratch, and tinyproxy without a pid file under a non-writable path (verify `-d` foreground needs no writable `/var/run`).
- [X] T022 [P] [US2] Add `pilot/images/worker/kelos_entrypoint.sh` (`#!/usr/bin/env bash` then `exec /usr/local/lib/pilot/entrypoint.sh "$@"`), installed at `/kelos_entrypoint.sh` by the worker Dockerfile. Add a comment that it is a compatibility shim only (FR-010, no Kelos dependency).
- [X] T023 [US2] Add an arbitrary-UID smoke test step to `.github/workflows/pilot-images.yml`, run before pushing. For each built image, run `docker run --rm --user 1000123:0 --read-only --tmpfs /tmp:exec,mode=1777 …` with that image's tmpfs mounts:
  - worker: the entrypoint with a dummy `/in` that has no model config, expecting a frame with `error` set (it proves start-up, not model access);
  - tools: `grade.py` on a tiny generated fixture bundle, expecting a frame;
  - egress: tinyproxy starts and listens within 5 s.
  The build fails if any one fails.
- [X] T024 [US2] Write `specs/003-m2-kelos-backend/evidence/enterprise.md`:
  - the local results of the same three arbitrary-UID runs;
  - **a real worker job under an arbitrary UID (analysis C1):** run the GHCR worker image with `--user 1000123:0 --read-only` and the pod's tmpfs mounts, with the operator's OpenCode config dir mounted read-only at `/home/worker/.config/opencode` (never copied into the repo or evidence), on the A task prompt from 002's fixture. Then grade the resulting bundle with the GHCR tools image, also under `--user 1000123:0 --read-only --network none`. Expected: the frame decodes, and the grade passes G1–G5 (or fails only on G5 if the induced prompt is used). Record tokens used and the result, with no secrets;
  - a proxy check: the worker image with `HTTPS_PROXY` pointing at the egress image on a docker network, reaching an allowlisted host and being refused for others;
  - a mirror check: `docker pull` by digest, `docker tag` and `docker push` to a scratch local registry, with `pilot up` against pins pointing there (can reuse `--local-build`'s registry container) showing the same digests.

**Checkpoint**: SC-003 met, including one real worker job and one grading run under an arbitrary UID (C1).

---

## Phase 5: User Story 3 — Kelos competitive review (Priority: P2)

**Goal**: A factual, publishable comparison on SB-1–SB-8 and a capability gap list.

**Independent Test**: `kelos-review.md` follows contracts/competitive-review-template.md. It has 8/8 SB rows for both products, each with a citation or "unverified", at least 5 capability rows, an attribution section, and no copied Kelos code.

- [X] T025 [P] [US3] Write the Kelos column of `specs/003-m2-kelos-backend/kelos-review.md` from research.md R2/R3. Re-verify each cited `path:line` against a fresh read-only clone of `kelos-dev/kelos` at `83a7405860df50e91e3313eb63b8e22f244fd943` (in the scratchpad, never inside the repo), and state facts as "default → configurable?".
- [X] T026 [P] [US3] Write the specfoundry column of `specs/003-m2-kelos-backend/kelos-review.md`, citing 002 and 003 evidence:
  - SB-1: P04, P09
  - SB-2: Dockerfiles, P10
  - SB-3: `backoffLimit: 0` in `pilot/manifests/worker-job.yaml.tmpl`, AU09
  - SB-4: constitution C-10, no telemetry code
  - SB-5: `pins.env` and `images.lock`, US1
  - SB-6: P06–P08, mutation test
  - SB-7: P02
  - SB-8: no cluster-wide controller (the orchestrator runs on the host with the operator's kubeconfig)
  Note 002's known limits honestly (e.g. a shared model key, the operator-account publisher identity).
- [X] T027 [US3] Write the capability table in `specs/003-m2-kelos-backend/kelos-review.md` with at least 5 rows: harness coverage, event triggers, sessions/console, spend budgets, install experience. Optionally add WorkerPools and pipelines. For each: the Kelos fact with a citation, our status (have/gap/won't do), and the constraint our version must keep (C-01–C-10, SB items). Add the "Ideas borrowed (attribution)" and "Proposed roadmap items" sections.
- [X] T028 [US3] Review `specs/003-m2-kelos-backend/kelos-review.md` for publishability (FR-013): every claim has a version and citation, no disparaging wording, no copied code blocks from Kelos (short field names and paths are fine), and the summary states the different goals neutrally.

**Checkpoint**: SC-006, SC-007 met.

---

## Phase 6: Polish & Cross-Cutting

- [X] T029 [P] Update `docs/harnesses.md`: the worker image now comes from GHCR, built in GitHub from upstream OpenCode; the arbitrary-UID and proxy notes; the Kelos-compatible entrypoint. Name no private providers.
- [X] T030 [P] Update `pilot/README.md`: `pilot up` pulls by digest (`--local-build` for development); where the images come from; the CI badge or workflow link.
- [X] T031 Update `specs/003-m2-kelos-backend/spec.md` with an **Evidence** section linking `evidence/ci.md`, `evidence/enterprise.md`, the validation run summary and `kelos-review.md`, and update the plan's Known risks with the outcomes.
- [X] T032 Run `/speckit-roadmap-debrief` for 003. Then, with owner approval, `/speckit-roadmap-write`: record 003's status, link its spec dir, and add any approved gap items from the review as new entries. Don't edit the roadmap directly.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: depends on T003. Blocks US1 code changes (T012–T015).
- **US1 (Phase 3)**: depends on Phase 2. T016–T019 need the owner (merge, package visibility, the human merge in the pilot).
- **US2 (Phase 4)**: T020–T022 can start after T008/T009 (same Dockerfiles, so sequence edits per file). T023 extends the workflow from T010.
- **US3 (Phase 5)**: independent of US1/US2; can run in parallel from the start. T026's SB-5 citation needs T017's digests.
- **Polish (Phase 6)**: after US1–US3.

### Key task dependencies

- T001 → T008, T009
- T002 → T012
- T004 → T005 → T013
- T006 → T012
- T007 → T013, T014
- T008 + T009 → T010 → T011 → T016 → T017 → T019
- T017 also checks the loop fix: merging the bot's `images.lock` PR starts **no** new `pilot-images` run (F1).
- T020–T022 → T023 → (rebuild) T024
- T025 + T026 → T027 → T028

### Parallel Opportunities

- Setup: T002 and T003, after T001.
- US1 tests: T006 and T007.
- US1: T008 and T009 (different Dockerfiles).
- US2: T020, T021 and T022 (different files).
- US3: T025 and T026 in parallel, and the whole of US3 alongside US1/US2.
- Polish: T029 and T030.

---

## Parallel Example: User Story 3 alongside User Story 1

```bash
Task: "Write Kelos column in specs/003-m2-kelos-backend/kelos-review.md"        # T025
Task: "Write specfoundry column in specs/003-m2-kelos-backend/kelos-review.md"  # T026
Task: "Change pilot/images/worker/Dockerfile to download + verify upstream OpenCode"  # T008
Task: "Change pilot/images/tools/Dockerfile to download + verify upstream spec"       # T009
```

---

## Implementation Strategy

### MVP first (US1)

1. Phases 1–2, then US1 through T015 (local code and workflow).
2. The owner merges the feature PR, makes the packages public, and merges the digest PR (T016–T017).
3. **Validate**: the pilot run on the GHCR images (T019). From here on, everyone pulls the same verified images.

### Incremental delivery

1. US1 → repeatable images.
2. US2 → enterprise-ready images, before 005 needs them.
3. US3 → positioning and roadmap input. It can be written any time.

### Owner actions (not automatable)

- Merge the feature PR and the bot's digest PRs.
- Set the GHCR packages to public, if the workflow can't.
- Merge A's draft PR during the validation pilot.
- Approve any roadmap items from the review.

---

## Notes

- [P] = different files, no dependencies on incomplete tasks.
- Nothing from Kelos is installed in pilot clusters, and no Kelos code is copied (FR-014, SC-007).
- The workflow never sees the publisher token or model keys.
