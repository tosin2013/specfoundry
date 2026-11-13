# Tasks: M0 stub isolation test

**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md)

- [x] T001 Stand up kind with Calico
- [x] T002 Run stub isolation suite (2026-11-12, other machine: 32 of 33 checks pass)
- T003 Read-only review of Kelos: moved to roadmap entry 003 on 2026-11-13 (no written review in this repo)
- [x] T004 Rebuild the suite in this repo as test/isolation/run.sh (the original failing check is not traceable; superseded by the rebuild)
- [x] T005 Record evidence in [evidence/20261113T014128Z/summary.md](evidence/20261113T014128Z/summary.md)
- [x] T006 Re-run end to end: 37 of 37 pass, including verified teardown (T01, T02)
- [x] T007 Mutation test: with the worker NetworkPolicies removed, the denied, grader and internet probes connect
