# M1 pilot run 20261113T030655Z

**State:** succeeded

**Elapsed:** 666 s total, 528 s excluding the human merge wait

**Mode:** `{"name": "step-by-step", "retry_limit": 2, "spend_cap_usd": 1.0, "token_cap": 2000000, "worker_deadline_s": 1200}`

## Attempts

| Task | Attempt | Induction | Grade | Cost (USD) | Tokens |
|---|---|---|---|---|---|
| A | 1 | withheld-acceptance-section | fail (grade_fail) | 0.0 | 241769 |
| A | 2 | - | pass | 0.0 | 190896 |
| B | 1 | - | pass | 0.0 | 530301 |

## Draft PRs

- Task A: [https://github.com/tosin2013/craz3-pilot-fixture/pull/1](https://github.com/tosin2013/craz3-pilot-fixture/pull/1) (draft=True, author=tosin2013)
- Task B: [https://github.com/tosin2013/craz3-pilot-fixture/pull/2](https://github.com/tosin2013/craz3-pilot-fixture/pull/2) (draft=True, author=tosin2013)
- `checks/results.jsonl`: 32 of 32 pass
- `audit.jsonl`: 11 of 11 pass
- `teardown.jsonl`: 3 of 3 pass

## Events

| Seq | Stage | Task | Attempt | Event | Detail |
|---|---|---|---|---|---|
| 1 | run |  |  | run_started | tosin2013/craz3-pilot-fixture |
| 2 | gate | A |  | gate_allow | seq=1 OK |
| 3 | gate | B |  | gate_refuse | seq=2 DEP_UNSATISFIED:001 |
| 4 | mode |  |  | mode_confirmed | {"name": "step-by-step", "retry_limit": 2, "spend_cap_usd": 1.0, "token_cap": 2000000, "worker_deadline_s": 1200} |
| 5 | attempt | A | 1 | attempt_created | ns=pilot-w-a-1 induction=withheld-acceptance-section |
| 6 | attempt | A | 1 | attempt_running | localhost:5001/pilot-worker@sha256:934fd396efb8de8b45ffdcb57d00796033e7b37506080ea91ab68821ac1b8af3 |
| 7 | attempt | A | 1 | attempt_collected |  |
| 8 | grade | A | 1 | grade_started | pilot-g-a-1 |
| 9 | grade | A | 1 | grade_fail | G5_hidden_tests |
| 10 | gate | B |  | gate_refuse | seq=3 DEP_UNSATISFIED:001 |
| 11 | retry | A | 2 | retry_confirmed |  |
| 12 | attempt | A | 2 | attempt_created | ns=pilot-w-a-2 induction=None |
| 13 | attempt | A | 2 | attempt_running | localhost:5001/pilot-worker@sha256:934fd396efb8de8b45ffdcb57d00796033e7b37506080ea91ab68821ac1b8af3 |
| 14 | attempt | A | 2 | attempt_collected |  |
| 15 | grade | A | 2 | grade_started | pilot-g-a-2 |
| 16 | grade | A | 2 | grade_pass |  |
| 17 | publish | A | 2 | publish_started | pilot/20261113T030655Z/a |
| 18 | publish | A | 2 | pr_opened | https://github.com/tosin2013/craz3-pilot-fixture/pull/1 |
| 19 | gate | B |  | gate_refuse | seq=4 DEP_UNSATISFIED:001 |
| 20 | run |  |  | run_paused(awaiting-merge) |  |
| 21 | run |  |  | run_resumed | paused(awaiting-merge) |
| 22 | reconcile | A | 2 | reconcile_applied | 549f751854f8297769c3f544dc699e11e6cf4a55 |
| 23 | reconcile | A |  | merge_wait_seconds | 138 |
| 24 | status | A |  | task_verified | 549f751854f8297769c3f544dc699e11e6cf4a55 |
| 25 | gate | B |  | gate_allow | seq=5 OK |
| 26 | attempt | B | 1 | attempt_created | ns=pilot-w-b-1 induction=None |
| 27 | attempt | B | 1 | attempt_running | localhost:5001/pilot-worker@sha256:934fd396efb8de8b45ffdcb57d00796033e7b37506080ea91ab68821ac1b8af3 |
| 28 | attempt | B | 1 | attempt_collected |  |
| 29 | grade | B | 1 | grade_started | pilot-g-b-1 |
| 30 | grade | B | 1 | grade_pass |  |
| 31 | publish | B | 1 | publish_started | pilot/20261113T030655Z/b |
| 32 | publish | B | 1 | pr_opened | https://github.com/tosin2013/craz3-pilot-fixture/pull/2 |
| 33 | audit |  |  | audit_done | 10/10 |
| 34 | run |  |  | run_succeeded |  |
| 35 | teardown |  |  | torn_down | teardown.jsonl |
| 36 | audit |  |  | audit_done | 11/11 |

## Known limits

- Gate runs on the host (no published spec-status CLI image yet, PRD §8 ask 3).
- Grader uses `spec status --json`, not `verify-readiness` (report-only skill mode not shipped, PRD §8 ask 1).
- Reconcile is a deterministic pilot equivalent of the spec-status reconcile skill.
- Spend cap is enforced by the pilot watchdog and deadline unless a provider-side cap is declared (R2).
- Single-node kind only; multi-node policy enforcement not covered.
