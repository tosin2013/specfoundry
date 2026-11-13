# Feature Specification: M0 stub isolation test on kind with Calico

**Feature Branch**: `001-m0-isolation-stub`
**Created**: 2026-11-13 (retroactive; work done 2026-11-12)
**Status**: Verified 2026-11-13 (rebuilt suite passes 37/37)
**Roadmap**: `.specify/memory/roadmap.md` entry 001

## Context

Retroactive spec. M0 first ran on 2026-11-12 on another machine (32 of 33 checks passed);
that suite and its output were not brought into this repo. On 2026-11-13 the suite was
rebuilt here as `test/isolation/run.sh` from the requirements below, and the rebuilt suite
is now the canonical M0 suite. The original failing check is not traceable.

## User Scenarios

### Story 1: Prove a stub worker is isolated (P1)

As the operator, I can stand up kind with Calico, launch a stub worker in its own
namespace, and see checks confirm its isolation, so that real workers can follow
the same pattern (PRD S1, S2, S4, S6).

**Acceptance**:
1. Given a fresh kind cluster with Calico, when the suite runs, then every check passes.
2. Given the suite has run, when teardown runs, then no test namespaces or resources remain.

### Story 2: Read-only Kelos review (moved)

Moved to roadmap entry 003 (M2 Kelos backend) on 2026-11-13. No written review was in
this repo, and the wrap-vs-fork decision (C-05) belongs with the Kelos adapter work.

## Requirements

- **FR-001**: The worker runs alone in its own pod and namespace.
- **FR-002**: The worker's service account has token automount disabled.
- **FR-003**: Egress is denied except for an allowlist, enforced by Calico.
- **FR-004**: The namespace has a ResourceQuota and the pod has an active deadline.
- **FR-005**: The worker holds no SCM credential.
- **FR-006**: Results and teardown evidence are recorded in this repo.

## Success Criteria

- **SC-001**: Every check in `test/isolation/run.sh` passes, and every "blocked" network
  check has a control probe showing the same target is reachable without the policy.
- **SC-002**: Teardown verified and recorded (cluster and node containers gone).
- **SC-003**: Evidence (results, rendered manifests, versions, log) is committed under
  `evidence/<run-id>/`.

## Evidence

- [2026-11-13 run: 37 of 37 pass](evidence/20261113T014128Z/summary.md)
