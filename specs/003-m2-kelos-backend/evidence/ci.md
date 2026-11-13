# CI evidence: pilot-images workflow (003 US1)

## T016: pull_request run (build + smoke only, no push), 2026-11-13

- Repository: `tosin2013/specfoundry` (public; recreated with rewritten history, see notes)
- PR: https://github.com/tosin2013/specfoundry/pull/1
- Run: https://github.com/tosin2013/specfoundry/actions/runs/43475167213 (event `pull_request`, conclusion **success**)

| Step | Result |
|---|---|
| Build locally (upstream checksums verified inside the Dockerfiles) | success: `opencode: OK`, `spec: OK` |
| Smoke test as an arbitrary UID (US2) | success: worker frame decoded; grade pass; proxy refused a non-allowlisted host |
| Log in / Push with provenance and SBOM / digests / upload | **skipped** (pull_request; SC-005) |
| digest-pr job | **skipped** (pull_request) |

Note: the first attempt in the earlier private repository never started a runner (run
43472304169, failed in 3 s with no steps; GitHub's reason was not visible to the local
token). The repository was then recreated as public with history rewritten to remove the
model provider's host name from committed evidence, and the run above succeeded.

## T017: push run on main (publish + digest PR), 2026-11-13

- PR #1 merged by the owner. Push run: https://github.com/tosin2013/specfoundry/actions/runs/43476018211
  - Attempt 1: `build` **success** (images pushed with provenance + SBOM). `digest-pr` failed
    opening the PR: *"GitHub Actions is not permitted to create or approve pull requests"*
    (a new-repo default). The branch `pilot-images/5fc8e38c9a3c` was pushed and changed only
    `pilot/images.lock`.
  - The owner enabled *Settings → Actions → Workflow permissions → Allow GitHub Actions to
    create and approve pull requests*. Attempt 2 (re-run of the failed job): **success**.
- Digest PR: https://github.com/tosin2013/specfoundry/pull/2, author `app/github-actions`, files:
  `pilot/images.lock` only. Opening it started **no** workflow run.
- PR #2 merged by the owner (`be60a13`). That merge started **no** `pilot-images` run (the latest
  run stayed the 17:45:56Z publish run). **The rebuild loop is closed (analysis F1).**

### Published images (`pilot/images.lock` on main)

```text
WORKER_IMAGE=ghcr.io/tosin2013/specfoundry-pilot-worker@sha256:bff0da27b9d34a68ca57d33068ae9d73b42d24993ee7ac42f63481a1df8fb3c6
TOOLS_IMAGE=ghcr.io/tosin2013/specfoundry-pilot-tools@sha256:78c87dc4147a0e81525c3e821b274199a3a77489f6f04f34f0b1a6c4f97aa12b
EGRESS_IMAGE=ghcr.io/tosin2013/specfoundry-pilot-egress@sha256:db46773a79c3c41129364bdf0399b76717af1e99a339943c833aaa28759a452a
```

| Image | Anonymous pull (public) | Provenance attestation | SBOM (SPDX) |
|---|---|---|---|
| worker | yes (token 200, manifest 200) | present | present, 130 packages |
| tools | yes | present | present, 166 packages |
| egress | yes | present | present, 16 packages |

Checked with an anonymous GHCR token and `docker buildx imagetools inspect --format
'{{json .Provenance}}' / '{{json .SBOM}}'`. The packages were public without any manual
visibility change.
