# Data Model: Operator guide

## Operator guide (`docs/operator-guide.md`)

The sections, in order. contracts/guide-outline.md has each section's acceptance checks.

| # | Section | Spec |
|---|---|---|
| 1 | What you'll do, and what you'll get | US1 |
| 2 | How specfoundry keeps you safe (security model + known limits) | US3, FR-009 |
| 3 | Before you start (machine, accounts, tools) | FR-001, FR-013 |
| 4 | Install the tools | FR-001 |
| 5 | Prepare a throwaway fixture repo and a scoped token | FR-003 |
| 6 | Configure your model provider | FR-002 |
| 7 | Stand up | FR-004 |
| 8 | Run the pilot, every prompt explained | FR-004, FR-010 |
| 9 | The merge pause, then resume | FR-005 |
| 10 | Read the evidence and the audit | FR-006 |
| 11 | Tear down and confirm | FR-007 |
| 12 | When something goes wrong (links to troubleshooting) and how to ask for help | FR-008, FR-012 |
| 13 | What will change (004, 005, 007, 008), and macOS | FR-011, FR-013 |

## Troubleshooting entry (`docs/troubleshooting.md`)

| Field | Rule |
|---|---|
| `title` | short, starts with the visible symptom |
| `symptom` | the exact message or behaviour (quoted) |
| `cause` | one or two sentences |
| `fix` | the commands or steps; never "share your key" |
| `confirm` | how to check it worked |
| `source` | where it was seen (a research note, evidence path or commit) |

Required entries (spec Edge Cases): `no-api-key`, `cost-zero`, `token-writes-project`,
`token-expired`, `prompts-answer-no`, `image-pull-error`, `cni-hash-mismatch`,
`tag-only-image`, `open-pilot-pr`, `resume-not-merged`, `deadline-or-spend-cap`,
`actions-cannot-open-prs`, `leftovers`.

## Validation run (`specs/006-operator-guide/evidence/`)

| Item | Content |
|---|---|
| `<run-id>/` | standard pilot evidence (audit, checks, summary), produced on the fresh machine |
| `validation-log.md` | machine description (OS, CPU, RAM; no hostnames or IPs); per-section start time and duration; each hesitation, deviation or outside lookup with the guide fix it caused (commit link); total hands-on time; result of the local provider-name scan |

Rule: SC-001 holds when `validation-log.md` lists 0 outside lookups and the run's audit is
11/11 with teardown 3/3.
