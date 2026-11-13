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

## T017: push run on main (publish + digest PR)

Pending: merge of PR #1 by the owner.
