# Implementation Plan: M2 hardened images and Kelos competitive review

**Branch**: `003-m2-kelos-backend` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-m2-kelos-backend/spec.md` (roadmap 1.4.0,
constitution 1.1.0)

## Summary

1. **GitHub-built images (US1).**
   - A new GitHub Actions workflow builds `specfoundry-pilot-worker` (OpenCode v2.2.7 from
     upstream `anomalyco/opencode`, verified against the release's `SHA256SUMS`),
     `specfoundry-pilot-tools` (spec binary verified by pinned sha256) and
     `specfoundry-pilot-egress`.
   - It pushes them as public GHCR packages and opens a PR updating the digests in
     `pilot/images.lock` (outputs). That file is never a workflow trigger, so there is no
     rebuild loop (analysis F1); `pilot/pins.env` holds only the inputs.
   - `pilot up` pulls by digest by default; `--local-build` keeps the 002 path. The Calico
     manifest hash is pinned and checked.
   - A plain-Jobs pilot run on these images re-validates everything (SC-002).
2. **Enterprise-ready images (US2).** Arbitrary UID (group-0 writable paths), read-only
   root filesystem, proxy-only egress, mirrorable by digest; a Kelos-compatible entrypoint
   wrapper.
3. **Competitive review (US3).** `kelos-review.md` compares Kelos v0.64.0 and specfoundry
   on SB-1–SB-8 (Kelos evidence is in research R2), plus a capability gap list. No Kelos in
   pilot clusters.

## Technical Context

**Language/Version**: Python 3.12 stdlib; Bash; GitHub Actions YAML (new).

**Primary Dependencies**:
- carried over from 002: kind v0.27.0, kubectl v1.32.2, Calico v3.29.3 (now hash-checked);
- spec 0.2.0, verified by sha256;
- OpenCode v2.2.7 from upstream (`SHA256SUMS`);
- GHCR;
- GitHub-hosted runners (ubuntu, amd64).

**Storage**: files (`pins.env` inputs, `images.lock` outputs, evidence, review); GHCR packages.

**Testing**:
- `python3 -m unittest`: pins validation (digest-only), Calico hash check, image-source
  selection;
- a workflow run on a PR (build only) and on `main` (build and push);
- local arbitrary-UID read-only runs of each image;
- a full plain-Jobs pilot run on GHCR images, plus audit.

**Target Platform**: Ubuntu host (kind + Calico); GitHub Actions.

**Project Type**: CLI orchestrator plus CI workflow plus container images.

**Performance Goals**: image workflow ≤ 15 min; pilot ≤ 60 min excluding the merge wait.

**Constraints**:
- digests only;
- no secrets in images;
- digest updates only by PR;
- no Kelos installed, adapted or forked (FR-014).

**Scale/Scope**: 3 images, 1 registry (Quay later), 1 review document.

## Constitution Check

*GATE: checked before Phase 0 and after Phase 1. Result: PASS.*

| Principle | How the design meets it | Status |
|---|---|---|
| I. Roadmap is source of truth | The roadmap (1.4.0) and constitution (1.1.0) were amended first; the spec follows | ✅ |
| II. Gates fail closed | Gate unchanged. Missing or tag-only pins, an unreachable registry or a CNI hash mismatch all stop stand-up | ✅ |
| III. Evidence, not CI | CI only builds; status moves on pilot evidence and audit (SC-002) | ✅ |
| IV. Least privilege | Images hold no secrets. The workflow uses only its own `GITHUB_TOKEN` (`packages`, `contents` on a PR branch, `pull-requests`), never the publisher token or model keys. No third-party controller enters the cluster | ✅ |
| V. Humans approve, humans merge | Digest updates arrive as PRs you merge | ✅ |
| VI. Build on, don't rebuild | Upstream OpenCode and spec-status reused; Kelos treated as competitor and reference, ideas attributed, no code copied | ✅ |
| VII. Repeatable and portable (laptop + enterprise) | Public digest-pinned images; arbitrary UID; read-only root filesystem; proxy-only; registry parameter for a Quay mirror in 005 | ✅ |
| Security & Isolation, telemetry (C-10) | No telemetry added; images make no phone-home calls (OpenCode update and model-catalogue fetches stay disabled) | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/003-m2-kelos-backend/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── competitive-review-template.md
│   ├── image-workflow.md
│   └── image-source.md
├── kelos-review.md          # written during implementation
├── checklists/requirements.md
├── evidence/                # validation pilot run
└── tasks.md
```

### Source Code (repository root)

```text
.github/workflows/pilot-images.yml   # NEW
pilot/pins.env                       # inputs: + CALICO_SHA256, OPENCODE_RELEASE/ASSET_SHA256, SPEC_ASSET_SHA256
pilot/images.lock                    # NEW outputs: *_IMAGE digests (bot PR only; never a workflow trigger)
pilot/images/worker/Dockerfile       # upstream OpenCode + checksum; group-0 paths; /kelos_entrypoint.sh
pilot/images/worker/kelos_entrypoint.sh   # NEW: exec wrapper (FR-010)
pilot/images/tools/Dockerfile        # spec verified by pinned sha256; group-0 paths
pilot/images/egress/Dockerfile       # group-0 friendly
pilot/specfoundry_pilot/images.py    # load_pinned() default; build_all() for --local-build
pilot/specfoundry_pilot/cluster.py   # Calico hash check; local registry only with --local-build
pilot/specfoundry_pilot/cli.py       # `up --local-build`
pilot/specfoundry_pilot/evidence.py  # image_source in versions.txt / run.json
pilot/tests/test_pins.py             # NEW
```

**Structure Decision**: Extend the 002 layout. Add the repo's first workflow under
`.github/workflows/`.

## Phase status

- Phase 0: [research.md](research.md), R1–R8.
- Phase 1: [data-model.md](data-model.md), [contracts/](contracts/),
  [quickstart.md](quickstart.md).
- Phase 2: `/speckit-tasks`.

## Known risks

- Making a GHCR package public from a private repo may need a one-time package-settings
  change (*verify at implement*).
- The upstream OpenCode binary may differ from 002's host binary; SC-002 re-validates it.
- Arbitrary-UID support may surface file-permission issues in OpenCode's own state
  directories; R8's tests catch them.

### Outcomes (2026-11-13)

- **GHCR visibility:** the packages were public without any manual change (public repo). But
  a new repo blocks Actions from opening PRs by default; the owner enabled *Allow GitHub
  Actions to create and approve pull requests*.
- **Upstream OpenCode:** the binary is byte-identical to 002's host binary, so the grading
  and induction behaviour was unchanged (confirmed by the validation run).
- **Arbitrary UID:** no permission issues. All three images, and a real worker job, ran as
  UID 1000123.
- **New finding:** after the repo went public, the publisher-token scope check gave a false
  positive (GitHub's `permissions` field shows the account's rights on a public repo). It
  was replaced with a side-effect-free write probe.
- **Privacy:** the model provider's host is now recorded only as a hash. History was
  rewritten and the repo recreated before going public.

## Complexity Tracking

None.
