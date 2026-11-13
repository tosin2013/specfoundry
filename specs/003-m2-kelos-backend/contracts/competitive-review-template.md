# Contract: Kelos competitive review (`specs/003-m2-kelos-backend/kelos-review.md`)

Factual and publishable (FR-013): versions stated, citations for every claim, no
disparaging language, no copied Kelos code, borrowed ideas attributed. No Kelos component is
installed in pilot clusters (FR-014).

```markdown
# Kelos and specfoundry: a security-model comparison

**Compared**: Kelos v0.64.0 (83a7405) · specfoundry <commit> · **Date**

## Summary
<3–5 sentences: different goals (convenience-first agent runner vs governed,
least-privilege delivery for laptops and enterprise); headline differences.>

## Security bar
| SB | Requirement | Kelos v0.64.0 (default → configurable?) | specfoundry | Citations |
|---|---|---|---|---|
| SB-1 | No SCM credential in the worker |  |  |  |
| SB-2 | Own image, non-root, no sudo, digest |  |  |  |
| SB-3 | No automatic retry |  |  |  |
| SB-4 | No phone-home telemetry; operator observability only |  |  |  |
| SB-5 | All images pinned by digest |  |  |  |
| SB-6 | Isolation; egress via allowlist proxies; no shared storage with grader |  |  |  |
| SB-7 | Service-account token off |  |  |  |
| SB-8 | Platform-component privileges |  |  |  |

## Capabilities (enterprise expectations)
| Capability | Kelos | specfoundry | Constraint our version must keep |
|---|---|---|---|
| Harness coverage | … | have / gap / won't do |  |
| Event triggers (GitHub, Jira, …) | … |  |  |
| Interactive sessions / console | … |  |  |
| Spend budgets | … |  |  |
| Install experience | … |  |  |

## Probes (optional, throwaway cluster)
| ID | What | How | Observed |

## Ideas borrowed (attribution)
- <idea> — <Kelos doc/source link>

## Proposed roadmap items
- <gap> → suggested entry (to be added by the owner via /speckit-roadmap-write)
```

Rules:
- Every cell names a fact plus a citation, or says `unverified`.
- Kelos is described as of the pinned version only.
