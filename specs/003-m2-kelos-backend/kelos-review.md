# Kelos and specfoundry: a security-model comparison

**Compared**: Kelos v0.64.0 (`83a7405860df50e91e3313eb63b8e22f244fd943`, released 2026-11-08) ·
specfoundry at branch `003-m2-kelos-backend` (after 002 run `20261113T030655Z`) · **Date**: 2026-11-13

Kelos facts come from a read-only clone of `kelos-dev/kelos` at the commit above. Paths are
relative to that repository. specfoundry facts cite this repository's code and evidence. No
Kelos component was installed in any pilot cluster, and no Kelos code is copied here.

## Summary

Kelos and specfoundry both run coding agents in Kubernetes pods, but they aim at different
things:
- **Kelos** is a broad, convenience-oriented framework for defining and running agent
  workflows: tasks, sessions, pipelines, triggers and a console. By default the agent works
  in a repository workspace and can open pull requests itself.
- **specfoundry** is a governed delivery lifecycle for laptops and enterprise environments.
  A deterministic gate decides whether work may start, workers never hold SCM credentials,
  an independent grader judges the result, a separate publisher opens draft PRs, and a human
  merges.

Many of Kelos's defaults can be configured toward specfoundry's security bar (SB-1 to SB-7).
The main structural difference is SB-8: Kelos relies on a cluster-wide controller with broad
permissions, while specfoundry has no cluster-wide controller in the worker path.

## Security bar

"Default → configurable?" describes Kelos as shipped and whether documented configuration
changes it. It is not a judgement of Kelos's design goals.

| SB | Requirement | Kelos v0.64.0 (default → configurable?) | specfoundry | Citations |
|---|---|---|---|---|
| SB-1 | No SCM credential in the worker | **Default:** a Workspace with a `secretRef` puts `GITHUB_TOKEN`/`GH_TOKEN` and a token file into the agent pod, and the agent can open PRs itself. **Configurable:** the Workspace is optional, and `worker.credentials.type: none` needs no Secret, so the agent gets no Git token | The worker never holds an SCM credential. Only the `pilot-publish` namespace holds the token, and the publisher Job opens draft PRs | Kelos: `docs/agent-image-interface.md` §3 (env table: `GITHUB_TOKEN`, `KELOS_GITHUB_TOKEN_FILE`), §8; `docs/reference.md` "WorkerSpec", "Task Credential Secret Format". specfoundry: live checks P04, P09 (`specs/002-m1-gated-pilot/evidence/20261113T030655Z/checks/results.jsonl`) |
| SB-2 | Own image, non-root, no sudo, digest | **Default:** bundled agent images run as UID 61100 with passwordless sudo. **Configurable:** a custom `worker.image` replaces them; the contract is `/kelos_entrypoint.sh` with the prompt as `$1` | Thin images built in GitHub from checksum-verified upstream releases; non-root, no sudo (asserted at build time), arbitrary-UID capable, pinned by digest | Kelos: `opencode/Dockerfile:44-52`; `docs/agent-image-interface.md` §1, §2, §4. specfoundry: `pilot/images/*/Dockerfile`, live check P10, `specs/003-m2-kelos-backend/evidence/enterprise.md` |
| SB-3 | No automatic retry | **Default:** every Task Job gets `backoffLimit: 1`, so Kubernetes retries a failed pod once. **Configurable:** `spec.podFailurePolicy` is copied into the Job, so FailJob rules can stop retries | `backoffLimit: 0`; every retry needs the operator's typed confirmation, and the audit checks it | Kelos: `internal/controller/job_builder.go:489`, `:954`; `docs/reference.md` "Task Pod Failure Policy". specfoundry: `pilot/manifests/worker-job.yaml.tmpl`, audit AU09 |
| SB-4 | No phone-home telemetry; operator observability only | **Default:** a daily `kelos-telemetry` CronJob sends anonymous aggregate usage (counts, versions, total cost and tokens) as PostHog events; it states that no prompts, code or names are sent. **Configurable:** `telemetry.enabled: false` in the chart, or `kelos install --disable-heartbeat`. Prometheus metrics are also available | No phone-home telemetry. Third-party telemetry is disabled (OpenCode update and model-catalogue fetches are off in the image). First-party telemetry is limited to operator observability (C-10; not yet built, roadmap Q6) | Kelos: `docs/reference.md` "Telemetry", "Disabling Telemetry", "Prometheus Metrics"; `internal/manifests/charts/kelos/values.yaml:9-10`. specfoundry: constitution 1.1.0 Security & Isolation Constraints; roadmap C-10; `pilot/images/worker/Dockerfile` |
| SB-5 | All images pinned by digest | **Default:** chart images use `image.tag` (default `"latest"`), rendered as `<image>:<tag>`. **Configurable:** set each image value to `repo@sha256:…` with an empty tag (the templates omit `:tag` when the tag is empty) | Every pod image is a digest reference from `pilot/images.lock`; tag references are refused at stand-up | Kelos: `internal/manifests/charts/kelos/values.yaml:5-6`, `templates/deployment.yaml:33`. specfoundry: `pilot/specfoundry_pilot/images.py` (`validate_ref`), `pilot/tests/test_pins.py`, live check P10 |
| SB-6 | Isolation; egress via allowlist proxies; no shared storage with the grader | **Default:** no per-task network policy is created; the agent pod has the network access of its namespace. **Configurable:** Tasks run in their own namespace, and pod overrides cover volumes, security contexts, deadline, service account and labels, so a namespace with default-deny policies and a proxy can be prepared around them. The controller reads pod logs to collect structured outputs | One worker per pod and namespace with default-deny, quota and deadline; egress only via a domain-allowlisting proxy (C-07); results leave only as a framed log, with no shared writable storage (C-08). A mutation test shows the checks catch removed policies | Kelos: `docs/reference.md` Task table (`podOverrides.*`); `internal/controller/job_builder.go` (Job created in `task.Namespace`); no `NetworkPolicy` objects in `internal/`, `api/` or the chart templates (searched at the pinned commit); `internal/controller/output_parser.go:6-7`. specfoundry: P01–P08, `specs/002-m1-gated-pilot/evidence/20261113T030655Z/mutation.md` |
| SB-7 | Service-account token off | **Default:** Task pods don't set `automountServiceAccountToken`, so the service account's setting applies (Session pods set it to true). **Configurable:** `podOverrides.serviceAccountName` can point at a service account with automount disabled | Service account and pod both set automount false; no token file in the worker (checked live) | Kelos: `internal/controller/job_builder.go` pod spec (no automount field); `internal/controller/session_controller.go:1781`. specfoundry: P02 |
| SB-8 | Platform-component privileges | A cluster-wide controller (`kelos-controller-role`, a ClusterRole) with, among others: Secrets and ConfigMaps create/get/list/update/watch; pods (including `pods/log`); Jobs, CronJobs, Deployments, StatefulSets, Services and ServiceAccounts create/delete; Roles and RoleBindings create/delete. Webhooks require cert-manager. No namespace-scoped mode was found in the controller flags or chart values | No cluster-wide controller in the worker path. The orchestrator runs outside the cluster with the operator's own kubeconfig and creates per-attempt namespaces. In-cluster components (egress proxies, grader, publisher Jobs) have no Kubernetes API permissions | Kelos: `internal/manifests/charts/kelos/templates/rbac.yaml:4-194`; `templates/webhook.yaml:17,32`; `cmd/kelos-controller/main.go` (flags). specfoundry: `pilot/manifests/*.yaml.tmpl` (service accounts with automount off, no Roles), `pilot/specfoundry_pilot/cluster.py` |

## Capabilities (enterprise expectations)

| Capability | Kelos v0.64.0 | specfoundry | Constraint our version must keep |
|---|---|---|---|
| Harness coverage | Claude Code, OpenAI Codex, Google Gemini, OpenCode, Cursor, plus custom images (`README.md:39`) | **gap**: OpenCode only (others documented as "later", `docs/harnesses.md`) | Each harness in a thin, digest-pinned, no-sudo image (C-09); its key as a per-attempt Secret; egress via the model proxy (C-07) |
| Event triggers (GitHub, Jira, Linear, cron, webhooks) | TaskSpawner and WebhookGateway resources (`docs/reference.md` "TaskSpawner", "WebhookGateway"). Kelos documents that the generic webhook endpoint is currently unauthenticated, and recommends network-level restriction until HMAC validation lands (`docs/integration.md:390-396`, kelos-dev/kelos#1040) | **gap**: runs start only by an operator command | Triggers may only *propose* work; the spec-status gate still decides (C-01, C-02), and a human still confirms the mode (constitution V). Inbound events must be authenticated (e.g. signed webhooks) |
| Interactive sessions and web console | Session resources and a console (`docs/reference.md` "Session", "Console authentication and authorization") | **won't do (for now)**: interactive agent sessions conflict with gated, graded, audited units of work | If ever added: no SCM credential in the session pod, and every change still flows through grader → publisher → human merge |
| Spend budgets | TaskBudget: daily cost/token limits checked at admission, failing closed on errors (`docs/reference.md` "TaskBudget", "Budget Admission Behavior") | **have (per attempt) / gap (per period)**: the per-attempt watchdog caps cost or tokens; there's no daily or project budget | A period budget must fail closed at the gate and be recorded in evidence (constitution II, III) |
| Install experience | `kelos install` CLI with an embedded Helm chart; needs cert-manager (`README.md` "Quick Start"; `docs/reference.md` "`kelos install` Flags") | **have (laptop)**: `pilot up` on kind; **gap (enterprise)**: OpenShift install path (roadmap 005) | One documented command sequence with verified teardown; no cluster-wide third-party controllers in the worker path (constitution VII) |
| Multi-step pipelines | TaskPipeline with ordered stages and matrix fan-out (`docs/reference.md` "TaskPipeline") | **have, differently**: ordering comes from the roadmap's dependencies and the spec-status gate, not from in-cluster pipelines | Dependencies stay in the roadmap (C-01) |
| Pre-warmed workers | WorkerPool (`docs/reference.md` "WorkerPool") | **gap (low priority)**: each attempt starts a fresh pod and namespace | Fresh isolation per attempt must be kept; a pool must not share state between attempts |

## Probes

None were run. All facts above come from source and documentation at the pinned commit, so
no Kelos component was installed anywhere (FR-014). Items that would need a probe to confirm
runtime behaviour, such as whether `podFailurePolicy` stops a retry after an eviction, are
stated as documented configuration, not as tested behaviour.

## Ideas borrowed (attribution)

These are ideas only; no code is copied. Kelos is Apache-2.0
(https://github.com/kelos-dev/kelos).

- **The agent-image contract:** `/kelos_entrypoint.sh` with the prompt as `$1`. specfoundry's
  worker image ships a compatibility shim so teams that run Kelos can use it
  (`pilot/images/worker/kelos_entrypoint.sh`; Kelos `docs/agent-image-interface.md` §1–§2).
- **Admission-time spend budgets that fail closed:** Kelos `docs/reference.md` "Budget
  Admission Behavior". Candidate for a specfoundry period budget, see below.
- **Explicit pod failure policies on agent Jobs:** Kelos `docs/reference.md` "Task Pod
  Failure Policy". Candidate for disruption handling in specfoundry's worker Jobs.

## Proposed roadmap items

For the owner to consider via `/speckit-roadmap-write`; not added by this review.

1. **More harnesses** (Claude Code, Codex): one image per harness under C-09, same worker
   contract.
2. **Period spend budget** at the gate: daily or project limits, fail closed, recorded in
   evidence.
3. **Event-proposed runs** (e.g. a GitHub issue label proposes a roadmap item). The gate and
   the human mode confirmation still decide.
4. **Operator observability (Q6, C-10):** metrics, traces and events to an operator-run
   collector.
5. **Worker Job disruption handling:** an explicit `podFailurePolicy` so infrastructure
   disruptions are recorded distinctly from worker failures.
