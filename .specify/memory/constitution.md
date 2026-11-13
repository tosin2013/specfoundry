# specfoundry Constitution

## Core Principles

### I. The Roadmap Is the Source of Truth
The Spec Kit roadmap (`.specify/memory/roadmap.md`, speckit-roadmap shape) and `spec status`
JSON (schema 1.0) are the ONLY scheduling inputs. No item, issue or task is scheduled from
any other source. Roadmap status MUST match merged reality after every cycle; drift found by
`reconcile` is a defect to fix, not a note.
Rationale: status that drifts from reality makes every downstream gate meaningless.

### II. Gates Fail Closed (NON-NEGOTIABLE)
Whether work may start is decided by a deterministic CLI (`spec status`), never by an agent's
judgement. A blocked item, an unsatisfied dependency, or a gate that cannot be evaluated
(exit code 2) MUST stop the run. No worker ever starts on a blocked item.
Rationale: the core promise of the product is that ordering is enforced, not suggested.

### III. Evidence, Not CI, Defines Done
An item is recorded `verified` only when the evidence ladder supports it: dry run,
reconciliation, security checks, functional test and verified teardown, graded by an
independent grader. "CI passed" alone never moves status to `verified`. Every run writes an
auditable evidence record (inputs, image digests, gate result, grader report, PR link).
Rationale: status claims must be checkable after the fact by someone who was not there.

### IV. Least Privilege by Construction (NON-NEGOTIABLE)
One worker per isolated unit (its own pod and namespace). Workers never hold SCM credentials;
only the publisher does. The controller never holds a worker's model key; worker keys are
per-run Secrets with spend caps. The grader is not writable by the worker, and grading
material is never mounted into the worker.
Rationale: an agent cannot leak or misuse a credential it was never given.

### V. Humans Approve, Humans Merge
A human approves the roadmap, confirms the risk/mode suggestion before any loop is staged, and
merges every PR. The system opens draft PRs only and MUST NOT auto-merge or start a loop on
its own.
Rationale: autonomy is granted per decision, not assumed.

### VI. Build On, Don't Rebuild
Reuse spec-status, Spec Kit and existing skills rather than reimplementing them. Pod runners
(plain Kubernetes Jobs now, OpenShift next) and SCMs (GitHub, later Bitbucket) are pluggable
backends behind adapters, not the product. Agent runners such as Kelos are competitors and
design references, not dependencies: their ideas MAY be borrowed (respecting their licences),
but none is adopted unless it meets the project's security bar by configuration alone.
Forking a dependency requires a recorded decision showing the needed behaviour cannot be
achieved by wrapping it.
Rationale: the value is the governed, least-privilege lifecycle, not another agent runner.

### VII. Repeatable and Portable
The project targets two environments, and every feature MUST work in both or state why not:
- **Laptops:** kind with an enforcing CNI, about 8 GB free, on any approved Mac/Ubuntu/CI
  machine.
- **Enterprise:** OpenShift under the restricted SCC (arbitrary UID, no root, no sudo),
  mirrored or air-gapped registries (e.g. Quay), HTTP proxies, a small trust base (no
  cluster-wide third-party controllers in the worker path), and audit evidence a security
  team can review.

One documented command sequence stands up the stack, and teardown is verified. Docs stay
harness- and host-agnostic. Every external dependency (images, tools, manifests) is pinned
to an exact version or digest.
Rationale: a result that only reproduces on one machine is not evidence, and an enterprise
will not run what it cannot audit.

## Security & Isolation Constraints

- Egress is allowlisted by NetworkPolicy; a CNI that enforces it (Calico or Cilium) is
  required. kind's default CNI is not acceptable for isolation tests.
- Every worker unit has a ResourceQuota, an active deadline, and a service account with
  token automount disabled.
- Images are thin, non-root, without sudo, and pinned by digest.
- Every run respects a spend cap; loop caps map to deadlines and retry limits.
- No third-party telemetry: any dependency's telemetry is disabled.
- First-party telemetry is operator observability only: metrics, traces and events (e.g.
  OpenTelemetry or Prometheus) sent only to a collector the operator runs. Nothing leaves the
  operator's environment unless the operator configures it, and there is no phone-home usage
  telemetry. Telemetry never carries secrets, prompts or source code.

## Delivery Workflow & Quality Gates

Plan (constitution check → specify → clarify → plan → tasks) → issues → ready gate
(`spec status`) → route (risk + mode, human confirms) → isolated build → independent verify
→ publisher opens one draft PR (`Closes #N`) with evidence → human merges → `reconcile`
proposes `verified`, which unblocks dependents.

- Each step's output is committed before the next step consumes it.
- One draft PR per item or task.
- spec-status skills only propose changes; status edits are applied after human approval.

## Governance

This constitution supersedes other practice in this repository. Amendments are made with
`/speckit-constitution`, recorded in the Sync Impact Report, and versioned with semver:
MAJOR for removing or redefining a principle, MINOR for adding a principle or section, PATCH
for clarifications. Every spec plan MUST include a constitution check against Principles
I–VII; any deviation needs a recorded justification in the plan's complexity tracking.
Security & Isolation Constraints are reviewed on every PR that touches worker, grader or
publisher configuration.

**Version**: 1.1.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-13
