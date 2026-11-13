# Research: M2 hardened images and Kelos competitive review

**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-11-13

Kelos facts below were read from the source at **v0.64.0** (tag commit
`83a7405860df50e91e3313eb63b8e22f244fd943`, released 2026-11-08), cloned read-only. Paths
are relative to that repository. This is planning research. The formal SB-1–SB-8 scoring
happens in `kelos-review.md`, the first implementation checkpoint (R1).

---

## R1 — The review is a competitive analysis, not an adoption decision

- **Decision (rescoped 2026-11-13, roadmap 1.4.0):** `kelos-review.md` compares Kelos
  v0.64.0 and specfoundry on SB-1–SB-8, and lists the Kelos capabilities enterprises
  expect, as *have*, *gap* or *won't do*. Nothing about Kelos is installed in pilot
  clusters. Optional probes run on a throwaway kind cluster that is torn down afterwards.
- **Rationale:** You decided Kelos is a competitor and reference (constitution VI 1.1.0,
  C-05). The source evidence (R2) already shows its model conflicts with our least-privilege
  rules (SB-8 especially). So the useful output is positioning plus a gap list, not an
  adopt/reject verdict.
- **Superseded:** the earlier "security bar decides adoption" design (roadmap 1.3.0). R2
  below is kept as the Kelos column of the comparison.

## R2 — Kelos evidence for each security-bar item (the Kelos column of the review)

| SB | Kelos v0.64.0 evidence | Fixable by configuration? | Expected score |
|---|---|---|---|
| SB-1 no SCM credential | A GitHub token is injected only "when workspace has a `secretRef`" (`docs/agent-image-interface.md` §3, `GITHUB_TOKEN`/`GH_TOKEN`/`KELOS_GITHUB_TOKEN_FILE`). The Workspace is optional (`docs/reference.md` WorkerSpec: `worker.workspaceRef` "No"). `worker.credentials.type: none` needs no Secret (`docs/reference.md` "Task Credential Secret Format"). | Yes: no Workspace, `credentials: none`; the repo arrives through our own `/in` ConfigMap via `podOverrides.volumes` | likely pass |
| SB-2 our image, no sudo | Bundled images add passwordless sudo (`opencode/Dockerfile:44-52`). A custom `worker.image` is allowed; contract: `/kelos_entrypoint.sh`, prompt as `$1`, **UID 61100** (`docs/agent-image-interface.md` §1, §2, §4). | Yes: our own image meeting the contract, without sudo | likely pass |
| SB-3 no automatic retry | `backoffLimit := int32(1)` on every Task Job (`internal/controller/job_builder.go:489`, used at `:954`). `spec.podFailurePolicy` is copied into the Job unchanged (`docs/reference.md` "Task Pod Failure Policy"). | Yes: `podFailurePolicy` rules `FailJob` on any non-zero exit **and** on `DisruptionTarget` | likely pass (needs a probe: an evicted pod must not be retried) |
| SB-4 telemetry off | Daily `kelos-telemetry` CronJob sends PostHog events (`docs/reference.md` "Telemetry"). Chart `telemetry.enabled: true` (`internal/manifests/charts/kelos/values.yaml:9`); `kelos install --disable-heartbeat`. | Yes: `telemetry.enabled=false` + `--disable-heartbeat`; plus a default-deny egress NetworkPolicy on the Kelos namespace, allowing only DNS and the API server | likely pass (needs a probe) |
| SB-5 digest pins | Templates render `{{ image }}{{ if tag }}:{{ tag }}{{ end }}` (`templates/deployment.yaml:33`, `webhook-server.yaml:48`, …); chart default `image.tag: "latest"`. cert-manager is required (`templates/webhook.yaml:17`). | Yes: set `image.tag=""` and each `*Image` / `*.image` value to `repo@sha256:…`; install cert-manager from a pinned, hash-checked manifest | likely pass |
| SB-6 002 isolation, C-07, C-08 | Pod overrides cover `volumes`, `volumeMounts`, `podSecurityContext`, `containerSecurityContext`, `activeDeadlineSeconds`, `serviceAccountName`, `labels`, `resources` (`docs/reference.md` Task table). The Job is created in the Task's namespace (`job_builder.go` `Namespace: task.Namespace`), so our per-attempt namespace, quota and NetworkPolicies apply. | Yes: create the Task inside our `pilot-w-*` namespace; the same live checks | likely pass |
| SB-7 token off | Task pods do not set `automountServiceAccountToken` (only Sessions set it, to true: `internal/controller/session_controller.go:1781`). | Yes: `podOverrides.serviceAccountName` → our service account with automount false. P02 must judge the effective setting | likely pass |
| **SB-8 controller privileges** | The controller **ClusterRole** (`templates/rbac.yaml:4`), cluster-wide: **secrets/configmaps create,get,list,update,watch**; pods (incl. `pods/log`); jobs, cronjobs, deployments, statefulsets, services, serviceaccounts **create/delete**; **roles, rolebindings create/delete**. No namespace-scoped watch option in the controller (`cmd/kelos-controller/main.go`, chart values). | **No.** The controller can read the `pilot-publish` SCM token and create RBAC anywhere. Narrowing the ClusterRole would break its cluster-wide cache; only a separate cluster for the publisher would avoid it | **likely fail unless you accept the risk** |

- **Use in the review:** this table becomes the Kelos column. In the specfoundry column,
  cite 002's evidence for each item (e.g. P04/P09 for SB-1, `backoffLimit: 0` plus
  confirmed retries for SB-3, 002 plan Known limits for anything partial). The
  "configurable?" column is phrased as facts about Kelos's defaults and options, not as an
  adoption verdict.

## R3 — Ideas worth borrowing (attributed)

- **Candidates for the gap list:**
  - **The agent-image contract**, as a compatibility target (FR-010): `/kelos_entrypoint.sh`
    with the prompt as `$1` (`docs/agent-image-interface.md`).
  - **Explicit `podFailurePolicy`** on pilot Jobs, for disruption handling.
  - **Daily spend budgets** that fail closed at admission (`docs/reference.md` "TaskBudget"
    and "Budget Admission Behavior"), as a second, roadmap-level cap beside the
    per-attempt watchdog.
  - **Output markers**, a convention for structured results
    (`internal/controller/output_parser.go:6-7`).
  - **Triggers and sessions**, as possible later roadmap items, each needing the 002 gate
    and credential model.
- Any copied code would need the Apache-2.0 licence and NOTICE; FR-013 says none is copied.

## R4 — GitHub-built images (C-09), always

- **Decision:** A new workflow, `.github/workflows/pilot-images.yml`, builds the three
  images on changes under `pilot/images/**` or `pilot/pins.env` (and on manual dispatch):
  - **`specfoundry-pilot-worker`:**
    - base: the digest-pinned Debian base from `pins.env`;
    - OpenCode from **upstream `anomalyco/opencode` v2.2.7**, asset
      `opencode-linux-x64.tar.gz`, verified against the release's `SHA256SUMS` (both
      published on the v2.2.7 release, checked 2026-11-13);
    - no operator binary;
    - entrypoint unchanged.
  - **`specfoundry-pilot-tools`:** the `spec` binary from its upstream release, verified
    by checksum. The spec-status repo is owned by the project owner. If its release
    publishes no checksum, pin the sha256 in `pins.env` and verify against that.
  - **`specfoundry-pilot-egress`:** unchanged Alpine + tinyproxy.

  Images are pushed to `ghcr.io/tosin2013/specfoundry-pilot-*` as **public** packages. The
  workflow uploads a digest manifest and opens a PR that updates `pilot/pins.env`
  (`WORKER_IMAGE=…@sha256:…`). It never pushes to `main` directly.
- **Registry is a matrix input** (`registry`, `namespace`, `variant`). It has one entry
  now, GHCR. 005 can add Quay or an OpenShift variant without redesign.
- **Arbitrary UID:** home and work directories are group-0 owned and group-writable
  (`chgrp -R 0 … && chmod -R g=u …`), and entrypoints don't assume a fixed UID. That keeps
  an OpenShift mirror viable. The default runtime UID stays fixed (10001/10002/10003)
  for kind.
- **`pilot up`:**
  - by default, pull-by-digest from `pins.env` (`images.py` `load_pinned()`);
  - `--local-build` keeps today's `build_all()` path (local registry) as an explicit
    fallback;
  - the kind node pulls public GHCR images directly, so no pull secret is needed;
  - the local registry container is only started for `--local-build`.
- **Rationale:** Repeatable on any machine (constitution VII), with no operator-binary
  provenance. Public images need no pull secret (your choice).
- **Alternatives considered:** private GHCR plus a pull secret (one more credential);
  build-only CI with local images (doesn't help others repeat the pilot).
- **Verify at implement:**
  - GHCR package visibility can be set to public from a private repo (the package
    settings, or the first push via `GITHUB_TOKEN` with `packages: write`);
  - the upstream tarball's layout (binary path inside it);
  - whether the upstream binary's sha256 equals the host binary's
    (`589253d3…f5e1`). Record the result either way.

## R5 — Calico manifest hash (FR-016)

- **Decision:** Add `CALICO_SHA256` to `pilot/pins.env`. The value is the sha256 recorded
  by 002 (`pilot/.build/calico.sha256` from the 002 run, re-downloaded and confirmed at
  implement time). `cluster.up_cluster()` compares the download against it and stops on a
  mismatch, before `kubectl apply`.

## R6 — Kelos install and adapter: dropped

- The Kelos runner adapter, Kelos install, cert-manager and Kelos telemetry handling are
  out of scope (FR-014, C-05). The earlier design (roadmap 1.3.0) is kept in git history
  only.

## R7 — What stays unchanged

The gate, the mode and retry confirmations, grader, publisher, reconcile, audit, evidence
layout and live checks are reused unchanged. Plain Jobs is the only runner. `versions.txt`
and `run.json` gain `image_source` (`pinned` or `local-build`).

## R8 — Enterprise readiness of the images (US2)

- **Decision:**
  - Each Dockerfile makes its writable paths (home, `/work`, `/tmp` usage) group-0 owned
    and group-writable (`chgrp -R 0 … && chmod -R g=u …`), and entrypoints resolve `$HOME`
    instead of assuming a username.
  - Test with `docker run --user 1000123:0 --read-only` plus the same tmpfs mounts as the
    pods.
  - The proxy variables (`HTTPS_PROXY`, `https_proxy`, `NO_PROXY`) are already honoured
    by git, curl and Python `urllib`; this gets documented and tested.
  - The worker image also ships `/kelos_entrypoint.sh` (FR-010), a two-line wrapper that
    execs the pilot entrypoint. It adds no dependency.
- **Rationale:** OpenShift's restricted SCC assigns a random UID with group 0. Getting the
  images right now avoids redoing them in 005.
