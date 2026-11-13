<!--
SYNC IMPACT REPORT
==================
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
- **Scope (in):** written read-only Kelos review (security model, token handling,
  bundle-out, stage retry) as the input to C-05; Kelos adapter; pinned Kelos version
  with telemetry off; thin OpenCode reference image pinned by digest.
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

**Version**: 1.1.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-13
