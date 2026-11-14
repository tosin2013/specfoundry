# 006 validation log: fresh-machine run (owner)

Round 1: 2026-11-14. Cells marked `<…>` are still for the owner to fill from the validation machine.

Follow only `docs/operator-guide.md` from GitHub. Record everything below. Never paste secrets,
hostnames, IPs or personal data.

## Machine

- OS: <e.g. Ubuntu 24.04.x LTS>, architecture: <amd64>
- CPU: <n>, RAM: <GB>, free disk: <GB>
- Fresh? No prior specfoundry, kind, `~/.config/specfoundry`, `~/.config/opencode`: <yes/no>

## Sections

| Section | Start (UTC) | Duration | Hesitations / deviations / outside lookups | Guide fix (commit) |
|---|---|---|---|---|
| 3 Before you start | | | | |
| 4 Install the tools | | | | |
| 5 Model provider (was 6) | | | **F1** `publisher-token` failed: `pilot.env` didn't exist yet. **F2** (owner): reuse an existing OpenCode setup | b4868d6 (sections swapped, errors name the fix); a33427c, 0b04856 (`import-opencode`, `docs/providers.md`) |
| 6 Fixture repo + token (was 5) | | | **F3** first token was too broad (`canary_push: True`); the check caught it, but the failing token was still saved to `publisher.env` | this branch: only a token that passes the check is saved |
| 7 Stand up | | | | |
| 8 Run the pilot | | | none recorded. A/1 failed and A/2 passed, as designed (AU11 induction) | — |
| 9 Merge pause + resume | | | none recorded. Owner merged fixture PR #5 (A) and the B PR | — |
| 10 Read the evidence | | | none recorded | — |
| 11 Tear down | | | none recorded | — |

**Total hands-on time** (excluding downloads and model work): <min>
**Outside lookups** (source code, prior notes, help): <count>
**Run id / audit / teardown**: 20261114T160532Z / 11/11 / AU07 pass (teardown rows: <n>/3, owner to fill)

## Troubleshooting spot checks

| Failure triggered | Entry used | Resolved with the doc only? |
|---|---|---|
| tag-only image reference | | |
| wrong CNI hash | | |
| `pilot run` without a terminal | | |
| pilot PR left open before `run` | | |
| `resume` before merging | | |

## Privacy check

`grep -rniF '<model host>' docs/ specs/006-operator-guide/`: no output (2026-11-14; also the host's first label, the READMEs, and provider names: 0 matches)
`pilot/pilot audit --run 20261114T160532Z` AU08: pass (owner's machine)
