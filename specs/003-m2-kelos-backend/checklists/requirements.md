# Specification Quality Checklist: M2 hardened images and Kelos competitive review

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-13
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Kelos, kind, Calico, cert-manager and OpenCode are named because the roadmap entry and
  its decisions (C-05, C-06, C-07, C-08) fix them as scope, not as design choices made here.
- Iteration 1: two [NEEDS CLARIFICATION] markers (FR-004 fork scope, FR-006 which units).
  Iteration 2 (2026-11-13): resolved by the owner. If a fork is needed, 003 includes it
  (FR-004a–e). Kelos runs worker attempts only. All items pass.
- Iteration 3 (2026-11-13, roadmap 1.3.0): direction changed to security first. Added the
  security bar SB-1–SB-8 and the `do-not-adopt` outcome; fork removed (FR-004 replaced);
  US2/US4 conditional on adoption; new always-delivered US3 (GitHub-built public images,
  pulled by digest; C-09). All items still pass.
- Iteration 4 (2026-11-13, roadmap 1.4.0 / constitution 1.1.0): Kelos is a competitor, not a
  dependency. Spec rewritten: US1 GitHub-built images (P1), US2 enterprise-ready images
  (P2), US3 factual competitive review (P2); no Kelos install, adapter or fork (FR-014).
  All items pass.
- Iteration 5 (2026-11-13, after /speckit-analyze): F1 fixed (digests moved to
  `pilot/images.lock`, never a workflow trigger); C1 (a real worker job and grading under an
  arbitrary UID) and D1 (provenance and SBOM on every image, FR-004a, SC-005a) added. All
  items pass.
