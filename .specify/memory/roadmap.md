<!--
SYNC IMPACT REPORT
==================
Version change: none → 1.0.0
Bump rationale: initial creation from docs/prd.md (2026-11-12 draft) and constitution v1.0.0.

Changes this revision:
  - Added spec 001 — M0 stub isolation test (implemented; not verified: 32/33 checks pass)
  - Added specs 002–005 — M1 pilot, M2 Kelos backend, M3 GitHub loop, M4 in-cluster planning + OpenShift
  - Decisions recorded: C-01 … C-06
  - Open questions Q1–Q5 carried from PRD §11

Specs affected: 001, 002, 003, 004, 005
Open questions added/resolved: Q1–Q5 added; none resolved

Notes: one entry per PRD milestone (owner decision, 2026-11-13). Finer per-capability
entries may replace these later via supersession once Q4 (granularity) is decided.
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

## Planned Specs

### 001 — M0 stub isolation test on kind with Calico  [status: implemented]

- **Description:** Stub worker isolation test suite on kind with Calico, plus a
  read-only review of Kelos.
- **Outcome:** All isolation checks pass on kind with Calico, the evidence is
  recorded in the repo, and teardown is verified.
- **Scope (in):** kind cluster with Calico, namespace/NetworkPolicy/ResourceQuota/
  service-account checks for a stub worker, Kelos read-only review.
- **Scope (out):** real harness images, grader, publisher, GitHub integration.
- **Depends on:** none
- **Governed by:** C-03, C-06
- **Addresses:** docs/prd.md §9 M0
- **Spec dir:** specs/001-m0-isolation-stub
- **Notes:** Done 2026-11-12 with 32 of 33 checks passing. Recorded as
  implemented, not verified: one check fails and the evidence record is not yet in
  this repo.

### 002 — M1 pilot: two-task gate on kind with plain Jobs  [status: planned]

- **Description:** Codex's two-task pilot run with plain Kubernetes Jobs.
- **Outcome:** Task A's grade fails so task B stays blocked; A is retried and
  passes, then B runs; exactly one draft PR per task, opened by the publisher.
- **Scope (in):** gate stage using spec status, plain-Jobs runner, isolated worker
  namespace, separate grader, publisher Job, evidence record per run.
- **Scope (out):** Kelos, GitHub issue sync, in-cluster planning, OpenShift.
- **Depends on:** 001
- **Governed by:** C-01, C-02, C-03, C-04
- **Addresses:** docs/prd.md §9 M1, §10 first two metrics
- **Notes:** Proves the "no worker starts on a blocked item" metric. Machine
  choice is open (Q3).

### 003 — M2 Kelos backend  [status: planned]

- **Description:** Run the M1 pilot through Kelos behind an adapter.
- **Outcome:** Same pilot result as 002 with Kelos as the runner: namespace,
  policies, thin image, gate stage, publisher and separate grader all preserved.
- **Scope (in):** Kelos adapter, pinned Kelos version with telemetry off, thin
  OpenCode reference image pinned by digest.
- **Scope (out):** other harness images, OpenShift.
- **Depends on:** 002
- **Governed by:** C-03, C-05
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

## Open Questions

- Q1 — Final project name and repo location (new repo vs. inside the spec-status
  org). Interim home: GitHub repo tosin2013/specfoundry.
- Q2 — Kelos as wrapped dependency vs. fork (default: wrap, see C-05).
- Q3 — Which machine runs M1 and M2 (Ubuntu box, Mac, another lab machine).
- Q4 — Granularity: one worker run per roadmap entry, or per task or issue.
- Q5 — Worker model provider and spend cap defaults.

## Cross-Cutting Notes

- spec-status asks drafted in PRD §8 (report-only skills, per-item readiness exit
  code, CLI container image) gate 002 and 003 in practice; track them as upstream
  issues.

---

**Version**: 1.0.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-13
