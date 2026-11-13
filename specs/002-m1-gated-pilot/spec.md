# Feature Specification: M1 pilot — two-task gate on kind with plain Jobs

**Feature Branch**: `002-m1-gated-pilot`

**Created**: 2026-11-13

**Status**: Implemented. Pilot run 20261113T030655Z succeeded (audit 11/11); not yet recorded `verified` in the roadmap

**Roadmap**: `.specify/memory/roadmap.md` entry 002 (depends on 001, verified 2026-11-13)

**Input**: User description: "002" — roadmap entry 002: Codex's two-task pilot run with
plain Kubernetes Jobs. Task A's grade fails so task B stays blocked; A is retried and
passes, then B runs; exactly one draft PR per task, opened by the publisher.

## Context

M0 (spec 001) proved a single stub worker can be isolated on kind with Calico. M1 is the
first end-to-end pass through the governed lifecycle: gate → isolated build → independent
grade → publish → status update → next item unblocks. It deliberately exercises the
failure path (a failed grade must keep the dependent task blocked) before the success
path, because "no worker ever starts on a blocked item" is the product's core promise
(constitution II, PRD §10 first metric).

The pilot runs against a small **pilot fixture**: a throwaway Spec Kit project with its
own roadmap holding two items, A and B, where B depends on A. The fixture, not the
specfoundry roadmap itself, is what the pilot gates and updates.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A blocked task never starts (Priority: P1)

As the operator, I start the pilot and see the gate refuse to launch task B while task A
is not verified, and see that refusal recorded, so I can trust that ordering is enforced
by the gate rather than by the agent.

**Why this priority**: This is the core promise of the product. Without it, nothing else
in the pilot is worth proving.

**Independent Test**: Run only the gate stage against the fixture with A unverified; it
must refuse B, record the refusal, and create no worker for B. Also run it with the gate
input deliberately unreadable; it must refuse everything.

**Acceptance Scenarios**:

1. **Given** the fixture roadmap with A not verified and B depending on A, **When** the
   gate evaluates B, **Then** B is refused, no worker unit for B is created, and the
   evidence record shows the gate input and the refusal reason.
2. **Given** the gate cannot evaluate status (missing roadmap, malformed status output,
   status tool error), **When** any task is considered, **Then** no worker starts and the
   run stops with the reason recorded.
3. **Given** A is ready, **When** the gate evaluates A, **Then** A is allowed and exactly
   one worker unit is created for it.

---

### User Story 2 - A failed grade keeps the dependent blocked, a retry recovers (Priority: P1)

As the operator, I watch task A's first build fail its independent grade, see that B
stays blocked and no PR is opened for the failed attempt, then retry A, see it pass, get
its draft PR, and only then see B gated open, built, graded and published.

**Why this priority**: This is the full M1 outcome from the roadmap; it proves the gate
reacts to evidence rather than to a worker finishing.

**Independent Test**: One full pilot run from a fresh kind cluster to teardown, producing
an evidence record per stage and exactly two draft PRs.

**Acceptance Scenarios**:

1. **Given** A's first attempt produces output that fails grading, **When** grading
   completes, **Then** A is not marked verified, no PR is opened for that attempt, B is
   still refused by the gate, and the failed grade report is in the evidence record.
2. **Given** A has failed once, **When** the operator confirms a retry of A, **Then** a
   fresh isolated worker unit runs (nothing reused from the failed attempt except the
   inputs), and the retry counts against A's retry limit. If the operator declines, or
   no confirmation can be obtained, no attempt starts and the run pauses as
   `awaiting-retry`.
3. **Given** A's retry passes grading, **When** the publisher runs, **Then** exactly one
   draft PR is opened for A, containing the evidence summary, and no PR exists for the
   failed attempt.
4. **Given** A's draft PR has been merged by a human, reconciliation has proposed A as
   verified, and the operator has approved that change, **When** the gate re-evaluates
   B, **Then** B is allowed, built, graded and published as one draft PR.
5. **Given** A's draft PR is open but not yet merged, **When** the gate evaluates B,
   **Then** B is still refused (passing a grade alone never unblocks a dependent).
6. **Given** A has used all of its retries and still fails, **When** the run continues,
   **Then** A is left not verified, B is never started, and the run ends as failed with
   the reason recorded.

---

### User Story 3 - Credentials and isolation are auditable after the fact (Priority: P2)

As a reviewer who was not present for the run, I can read the evidence record and confirm
that every PR came from the publisher, no worker or grader held an SCM credential, the
grader was not writable by any worker, and teardown removed everything.

**Why this priority**: Required for the PRD §10 credential metric and for constitution III
(evidence, not CI, defines done), but it audits the run in Stories 1–2 rather than adding
new lifecycle behaviour.

**Independent Test**: Given only the committed evidence record of a completed run, a
reviewer can answer each audit question without access to the cluster.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the reviewer inspects the evidence record, **Then**
   each PR is attributed to the publisher identity and each worker unit's recorded
   configuration shows no SCM credential.
2. **Given** a completed run, **When** the reviewer inspects the evidence, **Then** it
   shows checks that the worker could not write to the grader's area and that grading
   material was never mounted into a worker.
3. **Given** a completed run, **When** teardown has run, **Then** the evidence shows the
   cluster and all pilot resources are gone.

---

### Edge Cases

- The gate tool's output is valid but reports a dependency it cannot resolve: treated as
  blocked (fail closed).
- A worker exceeds its deadline: the unit is stopped, the attempt counts as failed, and B
  stays blocked.
- A worker produces no bundle, an empty bundle, or a bundle that does not apply to the
  fixture's base revision: the attempt fails grading.
- The grader itself crashes or times out: treated as a failed grade, never as a pass.
- The publisher fails to open the PR: A is not recorded verified and B stays blocked; a
  re-run of the publisher must not create a second PR for the same task.
- Pilot PRs left open by an earlier run: `reset-fixture` closes them, and `pilot run`
  refuses to start while any open pilot PR exists on the throwaway repo, so every run
  starts from zero. Within a run, if the task's PR already exists (e.g. the publisher
  is re-run), the publisher records it and opens no second PR.
- The pilot is interrupted mid-run: teardown can still be run on its own and verified.

## Requirements *(mandatory)*

### Functional Requirements

**Gate**

- **FR-001**: The pilot MUST decide whether a task may start using only the fixture
  roadmap and the status tool's machine-readable output (C-01).
- **FR-002**: The gate MUST fail closed: a task is refused if it, or any dependency, is
  blocked or unsatisfied, or if status cannot be evaluated for any reason (C-02).
- **FR-003**: Until the status tool offers a per-item readiness exit code, the gate MUST
  derive readiness from the reported blocked count and per-dependency satisfaction (C-02).
- **FR-004**: Every gate decision (allow or refuse) MUST be written to the evidence record
  with its input snapshot and reason.

**Build (worker)**

- **FR-005**: Each attempt MUST run as exactly one worker in its own pod and its own
  namespace, created fresh for that attempt (C-03, PRD S1).
- **FR-006**: Each worker unit MUST have an egress allowlist enforced by the CNI, a
  resource quota, an active deadline, and a service account with token automount
  disabled — the same controls proven in 001.
- **FR-007**: Workers MUST NOT hold any SCM credential and MUST NOT have grading material
  mounted (PRD S2, S5).
- **FR-008**: A worker's only output is a change bundle plus a report, handed to the grader.
- **FR-009**: The worker MUST be a real model-driven coding harness that builds the task
  from the fixture's spec artifacts.
- **FR-009a**: Each worker MUST receive its model key as a per-run secret scoped to that
  one attempt, with a spend cap; the key is removed at the end of the attempt, and the
  orchestrating side never reads it (PRD S3).
- **FR-009b**: The worker's egress allowlist MUST include only what the harness needs to
  reach its model provider (and nothing that reaches the SCM).
- **FR-009c**: A's first attempt MUST fail grading by a deliberate, declared induction
  applied to the worker's inputs or budget for that attempt only — never by changing the
  grader or its material. The induction MUST be recorded in the evidence record, and the
  retry MUST run without it.

**Grade (verify)**

- **FR-010**: Grading MUST run in a separate namespace from every worker and MUST NOT be
  writable by any worker.
- **FR-011**: The grader MUST produce a pass/fail report per attempt; any grader error or
  timeout counts as fail.
- **FR-012**: A task MUST NOT be published or recorded verified unless its latest attempt
  passed grading.

**Publish**

- **FR-013**: Only the publisher MAY hold SCM write credentials, and it MUST open PRs as
  drafts only, never merge (C-04).
- **FR-014**: The publisher MUST open exactly one draft PR per task across the whole run,
  including retries and publisher re-runs.
- **FR-015**: Each draft PR MUST include the evidence summary for the passing attempt.
- **FR-016**: Draft PRs MUST target a dedicated throwaway GitHub repository that hosts
  the pilot fixture, never the specfoundry repository itself. The publisher's credential
  MUST be scoped to that one repository with the minimum permissions needed to push a
  branch and open a draft PR.

**Retry and status**

- **FR-017**: A failed task MAY be retried up to a fixed retry limit (2), and only after
  the operator explicitly confirms that retry. Each retry is a fresh attempt with its own
  evidence. The pilot never starts an attempt on its own.
- **FR-018**: A task becomes verified only after (1) its draft PR is merged by a human,
  (2) reconciliation proposes the status change, and (3) the operator approves it; the
  change is then applied to the fixture roadmap (constitution III, V).
- **FR-018a**: The pilot MUST pause after A's PR is opened and resume B's gate evaluation
  only when the operator signals that A's PR was merged; it MUST NOT merge on its own.
- **FR-019**: The gate MUST re-evaluate B only from the updated fixture roadmap, never
  from an in-memory "A passed" signal.
- **FR-023**: Before any worker is staged, the pilot MUST show the run's mode and caps
  and MUST NOT continue without the operator's explicit confirmation. The confirmation
  (mode, caps, time) is recorded in the evidence record.

**Evidence and repeatability**

- **FR-020**: Every run MUST write an evidence record containing inputs, image digests,
  every gate decision, every grader report, PR links, and teardown results (PRD F9).
- **FR-021**: The pilot MUST stand up from a fresh kind cluster with an enforcing CNI and
  tear down with verified removal, using one documented command sequence (C-06, N3).
- **FR-022**: All images and external tools MUST be pinned to an exact version or digest.

### Key Entities

- **Pilot fixture**: the throwaway Spec Kit project, hosted in its own GitHub repository,
  that the pilot operates on; holds the fixture roadmap (items A and B, B depends on A) and the base revision workers build on.
- **Task**: a fixture roadmap item (A or B) with a recorded status and dependencies.
- **Attempt**: one build of one task in one fresh worker unit; has a number, a bundle, a
  report, and a grade.
- **Gate decision**: allow or refuse for one task at one moment, with its input snapshot
  and reason.
- **Grade report**: pass/fail plus the checks run, for one attempt.
- **Draft PR**: the single published change for a task, linked to its passing attempt.
- **Evidence record**: the per-run audit trail tying all of the above together.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a full pilot run, task B is refused by the gate on every evaluation made
  while A is not verified, and zero worker units are created for B before A is verified.
- **SC-002**: A's first attempt fails grading, A's retry passes, then B passes — and the
  evidence record shows that exact order.
- **SC-003**: Exactly 2 draft PRs exist at the end of the run (one for A, one for B), 100%
  opened by the publisher, 0 merged by the system.
- **SC-004**: An audit of the evidence record finds 0 worker or grader units holding an
  SCM credential, and 0 worker writes to the grader's area.
- **SC-005**: Each gate failure-mode check (missing roadmap, malformed status, status
  tool error) refuses all tasks: 100% fail-closed.
- **SC-006**: From a machine with the prerequisites, the full pilot (stand-up, run,
  teardown) completes with one documented command sequence, and teardown leaves 0 pilot
  clusters or resources behind.
- **SC-007**: A reviewer can answer every audit question in Story 3 from the committed
  evidence record alone.
- **SC-008**: Each worker attempt's model spend stays within its declared cap, and the
  evidence record shows the cap and the observed spend per attempt.

## Assumptions

- Runs on this Ubuntu machine, where 001 was verified (resolves roadmap Q3 for M1 only;
  M2's machine stays open).
- Granularity is one worker run per task (A, B) — the pilot's two "tasks" are two fixture
  roadmap items (resolves roadmap Q4 for the pilot only).
- The retry limit is 2 retries per task (3 attempts total) unless planning finds reason
  otherwise.
- The runner is plain Kubernetes Jobs; Kelos, issue sync, in-cluster planning and
  OpenShift are out of scope (roadmap 002 scope-out).
- Operator approval of status changes and the "A was merged" signal are interactive
  confirmations during the run; launch of workers is operator-initiated (PRD F6 default:
  the human).
- The model provider, the harness image, and the per-attempt spend cap are chosen during
  planning (roadmap Q5 stays open until then). The harness must be thin, non-root and
  pinned by digest (PRD S6); using a real harness here does not pull Kelos or the
  003 reference image forward.
- The throwaway GitHub repository and a publisher credential scoped to it are created by
  the operator before the first run; their names are configuration, not part of the spec.
- Because the worker is model-driven, a run can fail for reasons outside the pilot's
  control (provider outage, model quality); such runs are recorded as failed, never
  retried silently beyond the retry limit.
- The status tool is spec-status 0.2.0, which has no per-item readiness exit code (the
  upstream ask in PRD §8 is not yet shipped).
- Risk rating (PRD F5) is out of scope for M1. Every task uses one fixed mode,
  `step-by-step`: one attempt at a time, each retry confirmed by the operator, at most
  2 retries, a $1 spend cap per attempt, and a 20-minute worker deadline. The operator
  confirms this mode at the start of every run, before any worker is staged.
- The operator accepted (2026-11-13) that the model key may be a long-lived provider key
  copied into a new Secret for each attempt and deleted with it, rather than a key
  created per run. The spend cap is enforced by the pilot watchdog and the deadline.
  Revisit in 003.
- The induced failure on A's first attempt keeps the pilot's order (fail → retry → pass)
  deterministic even with a real model; a retry that still fails is a genuine failure.
- The isolation controls and kind + Calico stand-up from 001 are reused, not re-proven
  from scratch.

## Evidence

- **[Run 20261113T030655Z: succeeded](evidence/20261113T030655Z/summary.md)** (2026-11-13, this
  machine, kind + Calico, plain Jobs, OpenCode 2.2.7):
  - **Order:** A/1 (induced) failed only on G5; B was refused 5 times; you confirmed the retry;
    A/2 passed; draft PR #1; B refused (unmerged); human merge after 138 s; reconcile proposed
    and you approved `001 → verified`; B allowed; B/1 passed; draft PR #2.
  - **Checks:** live checks 32/32, audit AU01–AU11 11/11, teardown T01–T03 3/3. The redaction
    scan used the real secret values and found none.
  - **Spend:** `token-fallback` (the provider reports `cost: 0`). 242k, 191k and 530k tokens
    against a 2M cap per attempt.
  - **Timing:** 528 s excluding the merge wait (goal ≤ 60 min).
  - **[Mutation test](evidence/20261113T030655Z/mutation.md):** deleting the worker
    NetworkPolicies made internet, github.com and the grader stand-in reachable, and a planted
    SCM-like Secret failed P04 and P09.
- [Run 20261113T030451Z: failed closed](evidence/20261113T030451Z/summary.md). The mode prompt
  could not read the terminal (a pilot bug, since fixed and regression-tested), so it counted
  as "no": `MODE_NOT_CONFIRMED`, and no worker was staged.
- Draft PRs: <https://github.com/tosin2013/craz3-pilot-fixture/pull/1> (merged by the
  operator) and <https://github.com/tosin2013/craz3-pilot-fixture/pull/2> (open draft).
