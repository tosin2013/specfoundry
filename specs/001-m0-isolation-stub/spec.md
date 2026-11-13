# Feature Specification: M0 stub isolation test on kind with Calico

**Feature Branch**: `001-m0-isolation-stub`
**Created**: 2026-11-13 (retroactive; work done 2026-11-12)
**Status**: Implemented, not verified
**Roadmap**: `.specify/memory/roadmap.md` entry 001

## Context

Retroactive spec. M0 was run before this repository existed. This file records what
it was meant to prove so the roadmap entry can be gated and later verified.

## User Scenarios

### Story 1: Prove a stub worker is isolated (P1)

As the operator, I can stand up kind with Calico, launch a stub worker in its own
namespace, and see checks confirm its isolation, so that real workers can follow
the same pattern (PRD S1, S2, S4, S6).

**Acceptance**:
1. Given a fresh kind cluster with Calico, when the suite runs, then every check passes.
2. Given the suite has run, when teardown runs, then no test namespaces or resources remain.

### Story 2: Read-only Kelos review (P2)

As the operator, I have a written read-only review of Kelos that informs the wrap-vs-fork
decision (PRD Q2, roadmap C-05).

## Requirements

- **FR-001**: The worker runs alone in its own pod and namespace.
- **FR-002**: The worker's service account has token automount disabled.
- **FR-003**: Egress is denied except for an allowlist, enforced by Calico.
- **FR-004**: The namespace has a ResourceQuota and the pod has an active deadline.
- **FR-005**: The worker holds no SCM credential.
- **FR-006**: Results and teardown evidence are recorded in this repo.

## Success Criteria

- **SC-001**: 33 of 33 checks pass (2026-11-12 run: 32 of 33).
- **SC-002**: Teardown verified and recorded.
