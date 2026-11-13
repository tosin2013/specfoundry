# Implementation Plan: M0 stub isolation test

**Spec**: [spec.md](spec.md) · **Roadmap**: entry 001

## Summary

Retroactive plan for the 2026-11-12 M0 run: kind + Calico, stub worker namespace with
NetworkPolicy, ResourceQuota, deadline and a non-automounting service account, and a
check suite over them. Plus a read-only Kelos review.

## Constitution Check

- II Gates fail closed: n/a (no gate yet).
- III Evidence defines done: met for M0 scope. Evidence is committed under `evidence/`, the
  negative checks carry control probes, and a mutation test (policies removed) made the
  blocked probes connect, so they cannot pass vacuously.
- IV Least privilege: this is what M0 exercises.
- VII Repeatable: one command (`test/isolation/run.sh`); kind v0.27.0, kubectl v1.32.2,
  Calico v3.29.3 and the busybox image are pinned; teardown is verified (T01, T02).

## Structure

- `test/isolation/tools.sh`: pinned kind and kubectl, checksums verified
- `test/isolation/kind-config.yaml`: default CNI disabled, Calico pod subnet
- `test/isolation/manifests.yaml`: worker, allowed, denied, grader, control, deadline namespaces
- `test/isolation/run.sh`: up, checks C01–C35, evidence, teardown T01–T02

## Known limits

- The grader namespace is a stand-in (an HTTP target), not the real grader. Real grader
  isolation is re-proved in 002.
- Single-node kind; multi-node policy enforcement is not covered.
