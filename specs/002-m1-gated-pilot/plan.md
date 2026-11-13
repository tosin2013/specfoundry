# Implementation Plan: M1 pilot — two-task gate on kind with plain Jobs

**Branch**: `002-m1-gated-pilot` | **Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-m1-gated-pilot/spec.md`

## Summary

Build a host-side pilot orchestrator (`pilot/`, Python 3.12 stdlib) that drives one
governed cycle for a two-item fixture roadmap (A, then B that depends on A) held in a
throwaway GitHub repo:

- **Gate:** `spec status --json` on a fresh clone of the fixture, fail closed (R3).
- **Build:** each attempt is an isolated plain Kubernetes Job running the OpenCode
  v2.2.7 harness. A provider the operator configures sits behind a domain-allowlisting
  egress proxy, with a $1 spend cap per attempt (R1, R2, R4).
- **Grade:** an independent grader Job in its own namespace runs hidden tests and spec
  status on the result (R7).
- **Publish:** a publisher Job, the only holder of a repo-scoped token, opens one draft
  PR per task (R8).
- **Status:** the run pauses for a human merge, then reconciles and asks the operator
  to approve `A → verified` before B is gated again (R9).

A's first attempt is made to fail by a declared prompt induction (R6). Everything is
written to a committed evidence record and audited from files alone (R12).

## Technical Context

**Language/Version**: Python 3.12 (stdlib only) for the orchestrator; Bash for image
entrypoints and the `pilot/pilot` shim.

**Primary Dependencies**: kind v0.27.0, kubectl v1.32.2, Calico v3.29.3 (all as in 001);
spec-status `spec` 0.2.0 (commit `be08053`); OpenCode v2.2.7 (operator binary, sha256 in
R1); tinyproxy (Alpine, digest-pinned); `registry:2` (digest-pinned); `gh` and git on
the host (operator identity; reads plus the approved status push only).

**Storage**: Files only. The evidence record lives under
`specs/002-m1-gated-pilot/evidence/<run-id>/`, run state in `run.json`, and the
fixture roadmap in the throwaway repo.

**Testing**: `python3 -m unittest` for the gate matrix, frame parsing, reconcile rules,
redaction scan and audit. The full pilot run is the integration test. Live isolation
checks P01–P10 run during the run, and the evidence audit AU01–AU11 runs after it.

**Target Platform**: A single Ubuntu host with Docker and about 8 GB free (this
machine: 31 GB RAM, 8 CPUs), running kind with Calico.

**Project Type**: CLI orchestrator plus container images and Kubernetes manifests.

**Performance Goals**: A full pilot excluding the human merge wait finishes in ≤ 60
minutes. Per-unit deadlines: worker 20 min, grader 5 min, publisher 5 min.

**Constraints**:
- At most $1 spend per attempt, and at most 3 attempts per task.
- No worker or grader holds an SCM credential.
- No shared writable storage between worker and grader.
- All images are pinned by digest.
- The system never merges.

**Scale/Scope**: 2 tasks, at most 6 worker attempts, 1 cluster, 1 operator.

## Constitution Check

*GATE: checked before Phase 0 and re-checked after Phase 1 design. Result: PASS, with
one recorded deviation (see Complexity Tracking).*

| Principle | How the design meets it | Status |
|---|---|---|
| I. Roadmap is source of truth | The gate's only inputs are the fixture roadmap and spec-status JSON (R3). B re-gates from a fresh clone, never from memory (FR-019). | ✅ |
| II. Gates fail closed | 7-rule allow test. Any other outcome, including exit 2, bad JSON or an inconsistent count, refuses (exit 10). A unit-tested matrix proves it (SC-005). | ✅ |
| III. Evidence, not CI | The grader is independent. Status moves only after merge, reconcile and approval. Every run writes an audited evidence record, and the redaction scan must be clean. | ✅ |
| IV. Least privilege | One worker per pod and namespace. The model key is a per-attempt Secret deleted with the namespace. The SCM token exists only in `pilot-publish`. The grader namespace has no secrets and no egress. P01–P10 prove it live. | ✅ (see deviation 1) |
| V. Humans approve, humans merge | The operator confirms the run mode (`step-by-step`, fixed in M1 because risk rating is out of scope) before any worker is staged, confirms every retry, merges PRs on GitHub, and approves the status edit. There is no merge code path, and no attempt starts without a human `y`. | ✅ |
| VI. Build on, don't rebuild | Reuses spec-status (gate and grader), the OpenCode harness, and the 001 isolation pattern and tools. The runner sits behind an adapter so 003 can plug in Kelos. | ✅ |
| VII. Repeatable and portable | `pilot up`/`run`/`resume`/`down`. Everything pinned by version or digest. Teardown verified. The provider is configuration, and the docs are harness-agnostic. | ✅ |
| Security & Isolation Constraints | Enforcing CNI (Calico); allowlisted egress via proxies + NetworkPolicy; quota, deadline and no token automount on every unit; thin non-root digest-pinned images; spend cap; harness telemetry blocked by the proxy. | ✅ |

**Post-design re-check (after Phase 1)**: Contracts keep every rule above. The worker
frame comes only from the entrypoint, so the model cannot forge it. The publisher is the
only identity on PRs, which AU03 checks. The operator-credential status push (R9) is a
human action under V and is not a PR. Result: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-m1-gated-pilot/
├── spec.md
├── plan.md              # this file
├── research.md          # R1–R12 decisions
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── config.md
│   ├── worker-io.md
│   ├── gate-decision.schema.json
│   ├── grade-report.schema.json
│   └── evidence-record.md
├── checklists/requirements.md
├── evidence/            # written by pilot runs (committed)
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
pilot/
├── pilot                        # bash shim → python3 -m specfoundry_pilot
├── specfoundry_pilot/
│   ├── __main__.py / cli.py     # up, reset-fixture, run, resume, gate, audit, down, status
│   ├── config.py                # env-file loading, 0600 + name checks, repo guard
│   ├── gate.py                  # R3 rules → gate decision
│   ├── runner/
│   │   ├── base.py              # Runner interface (submit, wait, collect, delete)
│   │   └── jobs.py              # plain Kubernetes Jobs backend
│   ├── worker.py                # attempt namespace, inputs, prompt/induction, frame decode
│   ├── grader.py                # grader namespace + Job, grade.json
│   ├── publisher.py             # publisher Job, PR idempotency, prs.json
│   ├── reconcile.py             # merge check, tree match, propose/approve/apply
│   ├── checks.py                # live P01–P10
│   ├── audit.py                 # AU01–AU11 + redaction scan
│   ├── evidence.py              # run dir, events.jsonl, run.json
│   └── k8s.py                   # kubectl subprocess helpers
├── images/
│   ├── worker/{Dockerfile,entrypoint.sh,watchdog.py}
│   ├── tools/{Dockerfile,grade.sh,publish.sh}
│   └── egress/{Dockerfile,tinyproxy.conf.tmpl}
├── manifests/                   # templates: worker-ns, grader-ns, publisher-ns, egress proxies
├── fixture/                     # throwaway-repo template: .specify roadmap (001 A, 002 B), specs, src, visible tests
├── grading/                     # hidden tests (mounted only into grader namespaces)
├── kind-config.yaml             # cluster specfoundry-m1, default CNI off, registry mirror
└── tests/                       # unittest: gate matrix, frame, reconcile, redaction, audit
docs/
└── harnesses.md                 # harness options (OpenCode now; Claude Code, Codex, Copilot later) + provider config
test/isolation/tools.sh          # reused as is for pinned kind/kubectl
```

**Structure Decision**: The pilot is the first piece of product code, so it lives in a
top-level `pilot/` and not under `test/`. `test/isolation/` stays the M0 suite, and its
`tools.sh` is reused. The runner sits behind `runner/base.py` so 003 adds
`runner/kelos.py` without changing the gate, grader, publisher or evidence code.

## Phase status

- Phase 0 (research): done. See [research.md](research.md). No open
  NEEDS CLARIFICATION items. Four *verify at implement* items (R2, R4, R8, R10) become
  explicit tasks.
- Phase 1 (design): done. See [data-model.md](data-model.md), [contracts/](contracts/)
  and [quickstart.md](quickstart.md).
- Phase 2 (tasks): next, via `/speckit-tasks`.

## Known limits (carried into evidence and summary)

- The gate runs on the host, not in-cluster, because there is no published spec-status
  CLI image yet (PRD §8 ask 3).
- The grader uses `spec status --json` rather than `verify-readiness`, because the
  report-only skill mode is not shipped (PRD §8 ask 1).
- Reconcile is a deterministic pilot equivalent of the spec-status `reconcile` skill.
- With a provider that cannot cap per key, the spend cap is enforced by the pilot-side
  watchdog (and the deadline), not by the provider (R2).
- Single-node kind only. Multi-node policy enforcement is not covered (same as 001).

Confirmed by run 20261113T030655Z (2026-11-13). Additional limits found while implementing:
- **The publisher identity is the operator's account** (`tosin2013`), because a fine-grained
  token belongs to a user. AU03 checks author == publisher identity. A distinct `<app>[bot]`
  author needs a GitHub App, proposed for roadmap 004.
- **The provider reports `cost: 0`**, so the $1 cap ran as a 2M-token cap. Declaring model
  prices in the worker's `opencode.json` restores USD accounting (docs/harnesses.md).
- **Worker credentials are the OpenCode config directory** (`opencode.json` with a
  `{file:...}` key reference, plus the key file) mounted from a per-attempt Secret. Env-var
  keys did not authenticate.

## Complexity Tracking

| Deviation | Why needed | Simpler alternative rejected because |
|---|---|---|
| 1. The model key may be a long-lived provider key copied into a per-attempt Secret, rather than a truly per-run key (constitution IV: "worker keys are per-run Secrets with spend caps") | **Accepted by the operator 2026-11-13.** The operator chose a provider path without a per-key provisioning API. The Secret is still per attempt and deleted with the namespace, and the cap is enforced by the watchdog and deadline (R2). | Requiring a provider that provisions keys would override the operator's provider choice. Revisit in 003, or when the provider supports it. |
| 2. Two egress proxy deployments (model, SCM) | Calico OSS can't allowlist by domain, and S2 forbids the worker from reaching GitHub. | One shared proxy would let the worker reach GitHub. FQDN policies would mean changing the CNI proven in 001. |
| 3. A local registry container | Pods must reference images by `@sha256:` (S6), and images loaded with `kind load` have no registry digest. | `kind load` plus tag references would break digest pinning. |
