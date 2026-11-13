# 006 validation log: fresh-machine run (owner)

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
| 5 Fixture repo + token | | | | |
| 6 Model provider | | | | |
| 7 Stand up | | | | |
| 8 Run the pilot | | | | |
| 9 Merge pause + resume | | | | |
| 10 Read the evidence | | | | |
| 11 Tear down | | | | |

**Total hands-on time** (excluding downloads and model work): <min>
**Outside lookups** (source code, prior notes, help): <count>
**Run id / audit / teardown**: <run-id> / <n>/11 / <n>/3

## Troubleshooting spot checks

| Failure triggered | Entry used | Resolved with the doc only? |
|---|---|---|
| tag-only image reference | | |
| wrong CNI hash | | |
| `pilot run` without a terminal | | |
| pilot PR left open before `run` | | |
| `resume` before merging | | |

## Privacy check

`grep -rniF '<model host>' docs/ specs/006-operator-guide/`: <no output / findings>
`pilot/pilot audit --run <run-id>` AU08: <pass/fail>
