# Implementation Plan: M0 stub isolation test

**Spec**: [spec.md](spec.md) · **Roadmap**: entry 001

## Summary

Retroactive plan for the 2026-11-12 M0 run: kind + Calico, stub worker namespace with
NetworkPolicy, ResourceQuota, deadline and a non-automounting service account, and a
check suite over them. Plus a read-only Kelos review.

## Constitution Check

- II Gates fail closed: n/a (no gate yet).
- III Evidence defines done: NOT yet met; the evidence record is not in the repo and
  one check fails. Entry stays `implemented`.
- IV Least privilege: this is what M0 exercises.
- VII Repeatable: enforcing CNI (Calico) used per C-06; teardown evidence missing.

## Remaining work

See [tasks.md](tasks.md): fix the failing check, import evidence, record teardown.
