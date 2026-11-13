# Data Model: M1 pilot

**Spec**: [spec.md](spec.md) · **Research**: [research.md](research.md)

Every entity is stored as files: JSON in the evidence record, or Markdown in the fixture
repo. The pilot has no database.

## Pilot fixture

A throwaway Spec Kit project in its own GitHub repository (the throwaway repo).

| Field | Notes |
|---|---|
| `repo` | `owner/name` from config; name must end in `-pilot-fixture` and must not be this repo's own `origin` (repo guard, R9) |
| `default_branch` | usually `main` |
| `base_revision` | commit sha of the reset template; every attempt builds on it |
| `roadmap` | `.specify/memory/roadmap.md` with items `001` (task A) and `002` (task B → depends on 001) |
| `specs` | `specs/001-…/{spec.md,tasks.md}`, `specs/002-…/{spec.md,tasks.md}` |

The template lives in specfoundry at `pilot/fixture/`. Hidden grading tests live
separately at `pilot/grading/` and are never copied into the fixture repo or the worker.

## Task

A fixture roadmap item, as seen through `spec status --json`.

| Field | Source |
|---|---|
| `id` | `items[].id` (`001` = A, `002` = B) |
| `label` | `A` / `B` (pilot alias) |
| `status` | `items[].status` |
| `dependencies` | `items[].dependencies[]` (`id`, `satisfied`, `state`) |
| `tasks_checked/total` | `items[].tasks` |

**Status transitions in the fixture roadmap** (only through R9, operator-approved):
`planned → verified`. No other transition is written by the pilot.

## Gate decision

`evidence/<run>/gate/<seq>-<task>.json`, defined in
[contracts/gate-decision.schema.json](contracts/gate-decision.schema.json).

| Field | Notes |
|---|---|
| `seq` | monotonic per run |
| `task` | `A` / `B` |
| `decision` | `allow` / `refuse` |
| `reasons[]` | machine codes, e.g. `DEP_UNSATISFIED:001`, `UNEVALUABLE:exit_2`, `SCHEMA_MISMATCH`, `ALREADY_VERIFIED`, `INCONSISTENT_BLOCKED_COUNT` |
| `input.fixture_commit` | sha of the fresh clone the gate evaluated |
| `input.spec_status_exit` | process exit code |
| `input.spec_status_json_sha256` | hash of the raw JSON, which is stored next to it as `<seq>-<task>.status.json` |
| `at` | UTC timestamp |

Rule: `decision == allow` ⇔ every rule in R3 passes. A missing or unreadable decision
counts as `refuse`.

## Attempt

`evidence/<run>/attempts/<task>-<n>/`

| Field | Notes |
|---|---|
| `task`, `n` | n = 1..3 (retry limit 2) |
| `namespace` | `pilot-w-<task>-<n>` (lowercase) |
| `induction` | `withheld-acceptance-section` for A/1, else `null` |
| `image` | worker image `@sha256:` |
| `state` | see state machine below |
| `report` | `report.json`, defined in [contracts/worker-io.md](contracts/worker-io.md) |
| `spend` | `{cap_usd, cap_mode: cost/token-fallback, cost_usd, tokens}` |
| `grade` | `grade.json`, defined in [contracts/grade-report.schema.json](contracts/grade-report.schema.json) |

**Attempt state machine**

```text
created ─► running ─► collected ─► grading ─► passed
   │          │           │           │
   └──────────┴───────────┴───────────┴────► failed(reason)
reasons: deadline | spend_cap | no_result | bad_frame | oversize | harness_error
         | grade_fail | grader_error | grader_timeout
```

Validation: `passed` requires `grade.result == "pass"`. Every other end state is
`failed`. A task may publish only from a `passed` attempt.

## Run (task-level progress)

`evidence/<run>/run.json` holds the resumable state:

```text
A: gated ─► attempt(1..3) ─► publishing ─► published ─► awaiting-merge ─► reconciled ─► verified
                                 │
                                 └─► publish-failed (resumable; same passing attempt)
B: refused (while A ≠ verified) … gated ─► attempt(1..3) ─► published ─► awaiting-merge
run: in-progress | paused(awaiting-merge | awaiting-retry | awaiting-publish) | failed(reason) | succeeded | torn-down
mode: {name: "step-by-step", retry_limit, spend_cap_usd, token_cap, worker_deadline_s}  # confirmed at run start (FR-023)
```

The run succeeds when A and B each have exactly one draft PR, B's PR exists, and the
audit passes. Merging B and reconciling it to verified are outside the pilot outcome,
and the operator may do them afterwards.

## Draft PR

`evidence/<run>/prs.json`, a list of entries:

| Field | Notes |
|---|---|
| `task` | `A` / `B` |
| `number`, `url` | from GitHub |
| `head` | `pilot/<run-id>/<task>` |
| `draft` | must be `true` |
| `author` | login of the publisher token's identity |
| `attempt` | the passing attempt it was built from |
| `created` | `true` if created this call, `false` if found already existing (idempotent) |

Invariant: at most one entry per task. `author` ≠ the operator's login.

## Reconcile proposal

`evidence/<run>/reconcile/<task>.json`: `{task, pr_merged, merge_commit, tasks_percent,
tree_matches_graded, proposed: "planned→verified", approved: bool, applied_commit}`.

## Evidence record

`specs/002-m1-gated-pilot/evidence/<run-id>/`. The layout is in
[contracts/evidence-record.md](contracts/evidence-record.md).

## Check result

`checks/results.jsonl` and `teardown.jsonl` use the 001 row shape: `{id, requirement,
result: pass/fail, description, detail}`.
