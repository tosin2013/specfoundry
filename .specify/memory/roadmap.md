<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 1.2.0
Bump rationale: MINOR — new constraints (C-07, C-08), a new planned spec (006) and a
material scope change on 003, plus a status transition on 002.

Changes this revision (from debrief specs/002-m1-gated-pilot/roadmap-reviews/
debrief-20261113T032500Z.md, approved by the owner 2026-11-13):
  - Status: 002 planned → verified (pilot run 20261113T030655Z: checks 32/32, audit
    11/11, teardown 3/3, mutation test caught all; spec dir linked)
  - New constraints: C-07 (egress through per-role domain-allowlist proxies), C-08 (no
    worker-writable storage shared with the grader; results via framed logs)
  - Scope changed on 003: adds the Kelos adapter implementing runner/base.py and keeping
    C-07/C-08, and pinning plus checking the Calico manifest sha256
  - Note added on 004: GitHub App with per-run installation tokens for the publisher
  - New entry: 006 Operator guide (planned, depends on 002)
  - Open questions: Q3 decided for M1 (open for M2); Q4 decided for the pilot; Q5 partly
    decided
  - Cross-cutting notes: accepted per-run-key deviation; 002 workarounds for the
    spec-status asks

Specs affected: 002, 003, 004, 006
Open questions added/resolved: Q3 partly resolved (M1), Q4 resolved for M1, Q5 partly resolved

Previous revision 1.1.0 (2026-11-13):
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR — material scope change (Kelos read-only review moved from 001 to 003)
plus a status transition.

Changes this revision:
  - Status: 001 implemented → verified (rebuilt suite test/isolation/run.sh, 37/37 pass,
    evidence specs/001-m0-isolation-stub/evidence/20261113T014128Z, teardown verified)
  - Scope changed on 001: Kelos read-only review removed (no written review in repo)
  - Scope changed on 003: Kelos read-only review added as a required input to C-05

Specs affected: 001, 003
Open questions added/resolved: none

Notes: the original 2026-11-12 M0 run (32/33) was on another machine and is not
reproducible here; the rebuilt suite replaces it. Owner approved the move on 2026-11-13.

Previous revision 1.0.0 (2026-11-13): initial creation from docs/prd.md, entries 001–005,
decisions C-01 … C-06, open questions Q1–Q5.
-->

# specfoundry — Spec Roadmap

Living, non-binding map of the specs planned for specfoundry. It is **not a
commitment to order or scope** — it captures the spec-specific discussion,
decisions, technology choices, outcomes, and constraints surfaced during the
constitution and grilling phases so they are not lost before the spec that needs
them is written. Specs are scoped and clarified when they are actually started.
Foundations: the project [constitution](constitution.md) and the
[PRD](../../docs/prd.md).

Status legend (lifecycle): **undecided** · **needs-info** · **planned** ·
**specced** · **in-progress** · **implemented** · **verified** · **deferred** ·
**abandoned**.

---

## Vision & End States

- A human-approved Spec Kit roadmap is carried end to end: spec, plan, tasks,
  issues, isolated build, independent verification, draft PR, human merge.
- A roadmap entry becomes `verified` only when the evidence supports it, and that
  is what unblocks the next entry.
- No worker ever starts on a blocked item, and no worker ever holds an SCM
  credential (auditable from evidence records).
- From a fresh kind cluster to the first draft PR in one documented command
  sequence, with verified teardown.

## Constraints & Decisions

- **C-01 — Scheduling inputs:** only the roadmap and `spec status` JSON (schema
  1.0) schedule work (PRD F1, constitution I).
- **C-02 — Gate fails closed:** blocked or unevaluable means no start. Until
  spec-status ships a per-item readiness exit code, read `summary.blocked_count`
  and `dependencies[].satisfied` (PRD F4, constitution II).
- **C-03 — Isolation and credentials:** one worker per pod and namespace; only the
  publisher holds SCM write credentials; grader is separate and not writable by
  workers (PRD S1–S6, constitution IV).
- **C-04 — Human merge only:** draft PRs only, one per item or task, never
  auto-merge (PRD F8, constitution V).
- **C-05 — Wrap Kelos, don't fork:** fork only if token split, bundle-out or stage
  retry cannot be worked around (PRD Q2 default, constitution VI).
- **C-06 — Enforcing CNI:** isolation tests run on Calico or Cilium; kind's
  default CNI does not enforce NetworkPolicy (PRD S4).
- **C-07 — Egress through per-role allowlist proxies:** worker and publisher egress
  goes only through a domain-allowlisting proxy for their role (model hosts for
  workers, the SCM for the publisher). NetworkPolicy decides which namespace may reach
  which proxy, because Calico OSS cannot match domain names. A worker can never reach
  the SCM proxy (PRD S2, S4; decided in 002, research R4).
- **C-08 — No storage shared between worker and grader:** nothing writable is shared
  between a worker and the grader. Worker results leave only as a framed stdout result
  collected by the orchestrator; grading material lives only in grader namespaces (PRD
  S5; decided in 002, research R5).

## Planned Specs

### 001 — M0 stub isolation test on kind with Calico  [status: verified]

- **Description:** Stub worker isolation test suite on kind with Calico.
- **Outcome:** All isolation checks pass on kind with Calico, the evidence is
  recorded in the repo, and teardown is verified.
- **Scope (in):** kind cluster with Calico, namespace/NetworkPolicy/ResourceQuota/
  service-account checks for a stub worker.
- **Scope (out):** real harness images, grader, publisher, GitHub integration, Kelos
  review (moved to 003).
- **Depends on:** none
- **Governed by:** C-03, C-06
- **Addresses:** docs/prd.md §9 M0
- **Spec dir:** specs/001-m0-isolation-stub
- **Notes:** First run 2026-11-12 on another machine passed 32 of 33. Rebuilt
  here as test/isolation/run.sh; verified 2026-11-13 with 37 of 37 checks passing
  (including teardown), control probes for every blocked path, and a mutation test.
  Evidence: specs/001-m0-isolation-stub/evidence/20261113T014128Z.

### 002 — M1 pilot: two-task gate on kind with plain Jobs  [status: verified]

- **Description:** Codex's two-task pilot run with plain Kubernetes Jobs.
- **Outcome:** Task A's grade fails so task B stays blocked; A is retried and
  passes, then B runs; exactly one draft PR per task, opened by the publisher.
- **Scope (in):** gate stage using spec status, plain-Jobs runner, isolated worker
  namespace, separate grader, publisher Job, evidence record per run.
- **Scope (out):** Kelos, GitHub issue sync, in-cluster planning, OpenShift.
- **Depends on:** 001
- **Governed by:** C-01, C-02, C-03, C-04
- **Addresses:** docs/prd.md §9 M1, §10 first two metrics
- **Spec dir:** specs/002-m1-gated-pilot
- **Notes:** Proves the "no worker starts on a blocked item" metric. ~~Machine
  choice is open (Q3).~~ Ran on the Ubuntu host (31 GB, 8 CPUs), kind + Calico; one
  worker run per roadmap item (Q4 for M1). Verified 2026-11-13, run
  20261113T030655Z: A/1 failed grading (induced), B stayed refused, A/2 passed, draft
  PR #1 merged by the owner, reconcile approved, B passed, draft PR #2. Checks 32/32,
  audit 11/11, teardown 3/3, mutation test caught all. Evidence:
  specs/002-m1-gated-pilot/evidence/20261113T030655Z. Known limits are in the 002 plan.

### 003 — M2 Kelos backend  [status: planned]

- **Description:** Run the M1 pilot through Kelos behind an adapter.
- **Outcome:** Same pilot result as 002 with Kelos as the runner: namespace,
  policies, thin image, gate stage, publisher and separate grader all preserved.
- **Scope (in):** written read-only Kelos review (security model, token handling,
  bundle-out, stage retry) as the input to C-05; Kelos adapter; pinned Kelos version
  with telemetry off; thin OpenCode reference image pinned by digest; the Kelos
  adapter implements the 002 runner interface (`pilot/specfoundry_pilot/runner/base.py`)
  and keeps C-07 and C-08; pin and check the Calico manifest sha256
  (`CALICO_SHA256` in `pilot/pins.env`, checked by `pilot up`).
- **Scope (out):** other harness images, OpenShift.
- **Depends on:** 002
- **Governed by:** C-03, C-05, C-07, C-08
- **Notes:** Revisit per-run provider keys here (see Cross-Cutting Notes).
- **Addresses:** docs/prd.md §9 M2, F10

### 004 — M3 GitHub loop  [status: planned]

- **Description:** Tie roadmap entries, issues and PRs together on GitHub.
- **Outcome:** taskstoissues creates one issue per task, labels mirror spec status
  state, PRs carry Closes #N, and reconcile after merge shows no drift.
- **Scope (in):** issue creation, label sync, PR linking, post-merge reconcile.
- **Scope (out):** Bitbucket and other SCMs.
- **Depends on:** 003
- **Governed by:** C-01, C-04
- **Addresses:** docs/prd.md §9 M3, F3, F11
- **Notes:** Replace the publisher's fine-grained token with a GitHub App that mints a
  1-hour installation token per run, scoped to the target repo, so PRs show
  `<app>[bot]` rather than the owner's account. In 002 the token owner is the operator,
  which weakens PRD §10 metric 2 as seen from GitHub (the evidence audit still shows the
  publisher Job opened every PR).

### 005 — M4 in-cluster planning and OpenShift target  [status: planned]

- **Description:** Optional in-cluster planning Job, and OpenShift as a target
  platform.
- **Outcome:** Planning location is configurable per project (local or
  in-cluster) with the same handoff, and the pilot runs on OpenShift.
- **Scope (in):** planning Job, per-project planning setting, OpenShift runner
  validation.
- **Scope (out):** hosted SaaS or UI.
- **Depends on:** 003
- **Addresses:** docs/prd.md §9 M4, F2, N1
- **Notes:** In-cluster planning is optional per the PRD; OpenShift is the
  required part.

### 006 — Operator guide: repeat the pilot from zero  [status: planned]

- **Description:** End-user documentation so someone new can repeat the governed
  pilot on their own machine.
- **Outcome:** Someone new, starting from a fresh machine and using only the guide,
  stands up the stack, runs the pilot through both human gates, tears down, and gets a
  passing audit.
- **Scope (in):** prerequisites and machine sizing; provider setup (OpenCode config
  directory, `{file:}` key reference); publisher token creation and
  `pilot publisher-token`; the command sequence with every prompt; the merge pause;
  reading the evidence and audit; teardown; troubleshooting from 002's real failures;
  where 003 (Kelos) and 004 (GitHub App) will change the steps.
- **Scope (out):** hosted docs site or UI; naming specific private model providers.
- **Depends on:** 002
- **Governed by:** C-07
- **Addresses:** constitution VII ("one documented command sequence"), docs/prd.md N2, N3
- **Notes:** Requested by the owner 2026-11-13. Use run 20261113T030655Z as the
  worked example.

## Open Questions

- Q1 — Final project name and repo location (new repo vs. inside the spec-status
  org). Interim home: GitHub repo tosin2013/specfoundry.
- Q2 — Kelos as wrapped dependency vs. fork (default: wrap, see C-05).
- Q3 — Which machine runs M1 and M2 (Ubuntu box, Mac, another lab machine). **M1 decided
  2026-11-13:** the Ubuntu host (31 GB, 8 CPUs). Still open for M2.
- Q4 — Granularity: one worker run per roadmap entry, or per task or issue. **Decided
  for M1:** one worker run per roadmap item. Revisit in 004, where issues are per task.
- Q5 — Worker model provider and spend cap defaults. **Partly decided 2026-11-13:**
  harness OpenCode 2.2.7; provider is operator configuration (not named in docs); caps
  default to $1 per attempt with a 2M-token fallback when the provider reports no cost.
  Still open: provider choice for shared use, and USD accounting (declaring model
  prices).

## Cross-Cutting Notes

- spec-status asks drafted in PRD §8 (report-only skills, per-item readiness exit
  code, CLI container image) gate 002 and 003 in practice; track them as upstream
  issues. **002 workarounds in place:** the gate runs on the host (no CLI image); the
  grader uses `spec status --json` (no report-only `verify-readiness`); reconcile is a
  deterministic pilot step (the skill needs an agent). See the 002 plan, Known limits.
- **Accepted deviation (002):** constitution IV asks for per-run worker keys with spend
  caps. 002 copies a long-lived provider key into a per-attempt Secret (deleted with the
  attempt) and enforces the cap with the pilot watchdog and deadline. Accepted by the
  owner 2026-11-13; revisit in 003.

---

**Version**: 1.2.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-13
