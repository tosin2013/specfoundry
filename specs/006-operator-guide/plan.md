# Implementation Plan: Operator guide — repeat the pilot from zero

**Branch**: `006-operator-guide` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-operator-guide/spec.md`

## Summary

Write `docs/operator-guide.md`: the linear path from a fresh Ubuntu 24.04 machine to a
passing audit. It covers prerequisites, generic provider setup, the scoped publisher token,
the command sequence with every prompt explained using real output from run
`20261113T180203Z`, the merge pause, reading the evidence, teardown, a security-model section
for evaluators, and what changes as 004, 005, 007 and 008 land.

Alongside it:
- `docs/troubleshooting.md`, with the 11 real failures as symptom → cause → fix → confirm;
- a docs check (`pilot/tools/docs_check.py` plus a `docs-check` workflow) that keeps
  commands, paths, pinned versions and secret-free content correct in CI;
- README and `pilot/README.md` pointing at the guide.

Validation: you follow only the guide on a fresh machine, log every hesitation, fix the guide
for each finding, and commit the run's evidence.

## Technical Context

**Language/Version**: Markdown (GitHub-rendered). The docs check uses Python 3.12, stdlib only.

**Primary Dependencies**: none new. The docs check calls `pilot/pilot --help` and reuses
`specfoundry_pilot.audit` (redaction patterns) and `pilot/pins.env`.

**Storage**: files in the repo (`docs/`, `specs/006-operator-guide/evidence/`).

**Testing**:
- `python3 -m unittest` for the docs check (`pilot/tests/test_docs_check.py`), covering
  unknown subcommand/flag, missing path, version mismatch and token-like strings;
- the `docs-check` workflow on PRs;
- the fresh-machine validation run.

**Target Platform**: readers on Ubuntu 24.04 LTS amd64 (validated); macOS documented as
unsupported.

**Project Type**: documentation plus a small CI check.

**Performance Goals**: validator hands-on time ≤ 60 min, excluding downloads and model work
(SC-002).

**Constraints**:
- no secrets or private provider names in docs or evidence;
- every command, path and version must resolve against the repo;
- no hosted docs site.

**Scale/Scope**:
- 2 new docs: the guide (~10 sections) and troubleshooting (11+ entries);
- 1 check script, 1 workflow, plus README edits.

## Constitution Check

*GATE: checked before Phase 0 and after Phase 1. Result: PASS.*

| Principle | How the design meets it | Status |
|---|---|---|
| I. Roadmap is source of truth | Implements roadmap entry 006. The stale "003 Kelos" wording is to be fixed via `/speckit-roadmap-write` | ✅ |
| II. Gates fail closed | The guide explains (doesn't weaken) fail-closed prompts and stand-up checks; troubleshooting never advises bypassing them | ✅ |
| III. Evidence, not CI | 006 is verified by a real fresh-machine run with committed evidence and a validation log, not by the docs check alone | ✅ |
| IV. Least privilege | The guide teaches scoped tokens and per-attempt credential directories; troubleshooting never asks the operator to share secrets (FR-012) | ✅ |
| V. Humans approve, humans merge | The guide makes the human prompts and the merge explicit | ✅ |
| VI. Build on, don't rebuild | Reuses `audit.redaction_scan`, `pins.env` and the CLI's own `--help` for the docs check | ✅ |
| VII. Repeatable and portable | Delivers "one documented command sequence". Linux is validated; the macOS gap and the enterprise notes (mirroring, proxies, arbitrary UID) are stated honestly | ✅ |
| Security & Isolation | No telemetry; docs scanned for secret-like strings in CI; the provider host is checked locally by the validator | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/006-operator-guide/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── guide-outline.md      # required sections and their acceptance checks
│   └── docs-check.md         # what the docs check verifies, exit codes
├── checklists/requirements.md
├── evidence/                 # validation run + validation-log.md
└── tasks.md
```

### Source Code (repository root)

```text
docs/operator-guide.md                  # NEW: the guide
docs/troubleshooting.md                 # NEW: symptom-indexed entries
docs/harnesses.md                       # linked; small cross-links only
README.md                               # "Try the pilot" → short summary + link
pilot/README.md                         # link to the guide as user documentation
pilot/tools/docs_check.py               # NEW: docs check (stdlib)
pilot/tests/test_docs_check.py          # NEW
.github/workflows/docs-check.yml        # NEW: runs docs_check on PRs
```

**Structure Decision**: Operator docs live in `docs/`. The checker sits under `pilot/tools/`
so it shares the orchestrator's modules.

## Phase status

- Phase 0: [research.md](research.md), R1–R8.
- Phase 1: [data-model.md](data-model.md), [contracts/](contracts/),
  [quickstart.md](quickstart.md).
- Phase 2: `/speckit-tasks`.

## Known risks

- **The fresh-machine run needs a new token** if the current one expires (2026-12-13). The
  guide covers creating it, which the validation then exercises.
- **Docker install steps change upstream.** The guide links to Docker's official Ubuntu
  instructions and quotes only the stable commands.
- **Quoted outputs can drift** as the CLI evolves. The docs check covers commands and
  flags, not output text; output blocks are marked "from run 20261113T180203Z".

## Complexity Tracking

None.
