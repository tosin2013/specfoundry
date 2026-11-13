# Research: M1 pilot — two-task gate on kind with plain Jobs

**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-11-13

Each entry records a decision, why it was chosen, and what else was considered. Entries
marked *verify at implement* are settled in design. Their exact flags or values must be
confirmed against the pinned tool versions during implementation, and the task list
includes a step for each.

---

## R1 — Worker harness and model provider (PRD Q5)

- **Decision:** The worker harness is OpenCode **v2.2.7**, taken from the operator's
  installed binary (`$HOME/.opencode/bin/opencode`, sha256
  `589253d36810f21217edd51545cd435b328cdc3cf4f451fbe0cce6f88afcf5e1`) and baked into a
  thin worker image. The model provider is **operator configuration**, not part of the
  design. The operator supplies the OpenCode provider config and the key in a local env
  file outside the repo (see [contracts/config.md](contracts/config.md)). The pilot
  never names, hard-codes or prefers a provider.
- **Rationale:** The operator chose this (2026-11-13). It matches PRD §6 ("OpenCode
  first") without pulling 003's reference image forward. Keeping the provider out of
  the design keeps the docs harness-agnostic and host-agnostic (constitution VII, PRD N2).
- **Alternatives considered:** OpenRouter with per-attempt key provisioning. This had
  the strongest per-key cap, but the operator did not choose it. It stays documented as
  one supported provider option. Direct single-vendor APIs were not chosen as a default
  for the same reason. A scripted stub worker was rejected by the operator at spec time.
- **Docs:** `docs/harnesses.md` lists every harness option (OpenCode now; Claude Code,
  Codex and Copilot later) and how to configure a provider for each. All examples use
  generic or public endpoints.

## R2 — Spend cap of $1 per attempt (FR-009a, SC-008)

- **Decision:** Enforce the cap in two layers.
  1. **Pilot-side watchdog (always on):** The worker entrypoint runs OpenCode with
     `--format json` and reads its event stream. When the cumulative reported cost
     reaches `PILOT_SPEND_CAP_USD` (default `1.00`), it stops the harness and ends the
     attempt as `failed: spend_cap`. If the provider reports no cost (cost stays 0 while
     tokens grow), a token budget `PILOT_TOKEN_CAP` applies instead (default 2,000,000
     tokens) and the report marks the cap as `token-fallback`.
  2. **Provider-side cap (when the provider supports it):** Where the provider can issue
     per-key or per-run credit limits, the operator's config can set one. The evidence
     records whether a provider-side cap was declared.
  The attempt deadline (R6) is the final backstop.
- **Rationale:** The operator did not choose a provider that enforces per-key caps, so
  a cap the pilot controls must exist. Reading the harness's own event stream needs no
  proxy that inspects TLS traffic.
- **Alternatives considered:** A metering egress proxy, rejected because it would have
  to terminate TLS and so hold the key in plaintext outside the worker. Relying on the
  deadline alone, rejected because it doesn't bound money.
- **Verify at implement:** Which JSON event fields carry cost and tokens in OpenCode
  v2.2.7 (`opencode run --format json`). If neither exists, use the token budget only,
  and record that downgrade in this file.
- **Found 2026-11-13 (T030, from the v2.2.7 binary):** `--format json` prints one JSON
  object per line. Each step's end is `{"type":"step_finish", "part":{"type":"step-finish",
  "reason", "cost": <USD number>, "tokens":{"total"?, "input", "output", "reasoning",
  "cache":{"read","write"}}}}`. The watchdog sums `part.cost` and
  `input+output+reasoning` tokens across `step_finish` events, keyed by `part.id` so a
  step is never counted twice. Relevant env switches found in the binary:
  `OPENCODE_DISABLE_AUTOUPDATE`, `OPENCODE_DISABLE_MODELS_FETCH`,
  `OPENCODE_DISABLE_FREE_MODELS`, `OPENCODE_CONFIG_CONTENT`. A live check against the
  operator's provider is still needed. If a provider reports `cost: 0`, the token
  fallback applies.
- **Live check 2026-11-13 (operator's provider, OpenAI-compatible proxy):** `opencode run
  --format json` works headless and emits `step_start`, `text`, `step_finish`. The proxy
  reports `cost: 0` with real token counts (about 8.8k input tokens for a one-word reply,
  mostly system prompt). So by default the cap runs in `token-fallback` mode. To enforce
  the USD cap, the worker's `OPENCODE_CONFIG_CONTENT` should declare per-million-token
  prices on the model (`"cost": {"input": …, "output": …}`), so OpenCode computes
  `cost`. `docs/harnesses.md` explains this. The provider is configured through the
  OpenCode config file (`~/.config/opencode/opencode.json` on the host), not through
  `opencode auth`.

## R3 — Gate: deriving readiness from spec-status 0.2.0 JSON (FR-001–FR-004, C-02)

- **Decision:** The gate runs on the host against a **fresh clone of the fixture
  repo's default branch**, using `spec status --json --root <clone>` (spec 0.2.0, pinned
  by commit `be08053`). A task is **allowed** only if every one of these holds.
  Anything else is **refused**:
  1. the process exit code is 0 or 1 (2 = unevaluable → refuse);
  2. stdout parses as JSON with `schema_version == "1.0"`, `complete == true` and
     `error == null`;
  3. exactly one item has the task's id, with `status_known == true` and `active == true`;
  4. the item's status is one of `planned`, `specced` or `in-progress` (an item that
     is `implemented` or `verified` is not re-run);
  5. every entry in `dependencies[]` has `satisfied == true`;
  6. there are no diagnostics with `severity == "error"` for this item;
  7. a consistency check: if the item has any unsatisfied dependency then
     `summary.blocked_count` must be ≥ 1. If the global count and the per-item view
     disagree, refuse as inconsistent.
- **Rationale:** spec-status 0.2.0 has no per-item readiness exit code (PRD §8 ask 2).
  C-02 says to use `blocked_count` plus `dependencies[].satisfied`. `blocked_count` is
  global, so it serves as a cross-check, and the per-item dependencies decide. Cloning
  the default branch fresh means a human merge is what changes the gate's input
  (FR-019).
- **Alternatives considered:** Running the gate in-cluster, rejected because there is
  no published spec-status CLI image yet (PRD §8 ask 3); the host-side gate is
  recorded as a known limit. Parsing the human-readable output, rejected as unstable.

## R4 — Worker isolation and egress (FR-005–FR-008, FR-009b)

- **Decision:** Each attempt gets its own namespace `pilot-w-<task>-<attempt>`. It
  reuses the 001 controls: default-deny NetworkPolicy, ResourceQuota (`pods: 1`,
  `count/secrets: 1`), LimitRange, a service account without token automount, and a
  hardened pod spec (non-root, read-only root filesystem, no privilege escalation, all
  capabilities dropped). Egress is allowed only to cluster DNS and to the
  **model-egress proxy**. That proxy runs in namespace `pilot-egress-model`, and its
  domain allowlist holds only the operator-declared model host(s). It is the only route
  out. A separate **scm-egress proxy** (`pilot-egress-scm`, allowlist `github.com`,
  `api.github.com`) is reachable **only** from the publisher namespace.
- **Rationale:** Calico OSS NetworkPolicy cannot match domain names, and provider IPs
  change. A proxy that filters on domain, with NetworkPolicy deciding *who* may reach
  *which* proxy, gives a domain allowlist that can be audited. The proxy's deny log
  becomes evidence.
- **Alternatives considered:** Calico Enterprise or Cilium `toFQDNs`, which would mean
  changing the CNI proven in 001. IP CIDR allowlists, which are brittle. One proxy
  shared by worker and publisher, rejected because the worker could then reach GitHub
  (S2).
- **Proxy:** tinyproxy from a digest-pinned Alpine base, with `FilterDefaultDeny Yes`
  and allowlisted `CONNECT` to port 443 only.
- **Verify at implement:** tinyproxy's filter syntax for exact-host matching. OpenCode's
  use of `HTTPS_PROXY`. Which extra hosts OpenCode contacts at startup (models
  catalogue, update checks); disable them through its env/config, or let the proxy deny
  them and log the denials.
- **Verified 2026-11-13 (T034, tinyproxy 1.11.2-r0):** `FilterType ere`,
  `FilterURLs Off`, `FilterDefaultDeny Yes`, with allowlist lines like
  `^api\.github\.com$`, gives exact-host matching for `CONNECT`. Tested through the
  built image: `api.github.com` → 200; `github.com` and `example.com` → refused. A
  refusal logs `Proxying refused on filtered domain "<host>"`, which the pilot collects
  as `proxy-denials.log`.

## R5 — Moving the bundle and inputs without shared writable storage (FR-008, FR-010, S5)

- **Decision:**
  - **Into the worker:** a ConfigMap in the worker namespace holds a `git bundle` of the
    fixture base revision plus the task prompt, mounted read-only.
  - **Out of the worker:** the entrypoint sends the harness's own output to a file.
    Stdout carries only a framed result: `PILOT-RESULT-BEGIN`, then base64 of a tar
    holding `change.bundle` and `report.json`, then `PILOT-RESULT-END`. The orchestrator
    reads the result from `kubectl logs` after the Job finishes, checks its size
    (≤ 512 KiB) and framing, then deletes the namespace.
  - **Into the grader:** the orchestrator creates a ConfigMap with the bundle in the
    grader namespace. Grading material (hidden tests) is a second ConfigMap that exists
    only in the grader namespace.
- **Rationale:** No volume is shared between worker and grader, so the worker cannot
  write to the grader's area by construction. Logs need no exec into the pod and no
  `tar` in the worker image. Harness output never reaches stdout, so the model cannot
  forge the frame.
- **Alternatives considered:** A shared PVC, rejected because the worker could write to
  grader inputs (S5). `kubectl cp`, which needs a running pod and `tar`. An in-cluster
  object store, more moving parts than a 2-task pilot needs.

## R6 — Deadlines, retries and the induced first failure (FR-009c, FR-017, edge cases)

- **Decision:** Worker Job: `backoffLimit: 0`, `activeDeadlineSeconds: 1200`. Grader:
  300 s. Publisher: 300 s. **Retry limit: 2 retries (3 attempts) per task.** A retry is
  a new attempt in a new namespace. **The induction for A's attempt 1:** the task
  prompt is built from the fixture spec with the "Acceptance details" section left out.
  That section holds exact, non-guessable rules (e.g. a required constant and output
  format), and the hidden tests check them. The evidence names the induction
  `withheld-acceptance-section`. Attempt 2 receives the full prompt.
- **Rationale:** Leaving out non-guessable rules makes A's first attempt fail grading
  (not just fail to build) without touching the grader. The failure path then goes
  through a real grade report, as the roadmap outcome requires.
- **Alternatives considered:** A one-minute deadline on attempt 1, which would test the
  deadline and not grading. Corrupting the bundle, which tests the transport and not
  grading. Changing the grader, which FR-009c forbids.
- **Finding 2026-11-13 (T030, real runs):** removing the section from the prompt alone is
  **not enough**. The worker's checkout contains the full `spec.md`, and the model read it:
  the induced attempt passed G5. The fix is that the harness now runs in a history-free
  workspace (`/work/task`, from `git archive`), with the git checkout kept outside it
  (`/tmp/.pilot/repo`). For the induced attempt, the workspace `spec.md` is trimmed the same
  way as the prompt. The worker's changes are copied back and the original `spec.md` is
  restored before committing, so the bundle still applies to the real base.
  `induction.json` records `workspace_spec_trimmed`. Re-run result: G1–G4 pass, **G5 fails**
  (324k tokens). The non-induced attempt passes all five checks (186k tokens).

## R7 — Grader (FR-010–FR-012)

- **Decision:** Each attempt gets a grader Job in a fresh namespace
  `pilot-g-<task>-<attempt>` (no secrets, `count/secrets: 0`, egress denied entirely).
  It checks, in order: the bundle verifies and fast-forwards from the base revision;
  only allowed paths changed; the task's `tasks.md` items are all checked (via
  `spec status --json` on the result tree, using the same pinned binary baked into the
  tools image); the visible fixture tests pass; the hidden grading tests pass.
  It emits a framed `grade.json` the same way as R5. Any crash, timeout, missing or
  invalid frame counts as **fail**.
- **Rationale:** A fresh namespace per attempt prevents state leaking between
  attempts. Using spec status in the grader keeps "evidence, not CI" (constitution III)
  and reuses spec-status (VI). spec-status `verify-readiness` is a skill that needs an
  agent. Its report-only headless mode is PRD §8 ask 1, so the grader uses the CLI's
  JSON, recorded as a known limit.

## R8 — Publisher and draft-PR idempotency (FR-013–FR-016, edge cases)

- **Decision:** The publisher Job runs in `pilot-publish`, the only namespace holding the
  SCM Secret. That Secret is a fine-grained token scoped to the throwaway repo, with
  `contents: write` and `pull_requests: write` only. The Job pushes the passing bundle
  to branch `pilot/<run-id>/<task>` and opens a **draft** PR through the GitHub REST
  API, with the evidence summary in the body. **Idempotency:** before creating, it lists
  open PRs for that head branch. If one exists it records it and creates nothing. For
  earlier runs, `reset-fixture` (R9) closes leftover pilot PRs, so each run starts from
  zero PRs. The publisher has no merge code path.
- **Rationale:** The head branch is unique per run and per task, so "one PR per task"
  can be checked against GitHub alone, and re-running the publisher is safe.
- **Verify at implement:** fine-grained token permission names; the REST field for
  draft PRs (`draft: true`).

## R9 — Reconcile, approval, and who writes the fixture roadmap (FR-018, FR-018a)

- **Decision:** After A's PR opens, the run pauses in `awaiting-merge` and the
  orchestrator exits. The operator merges the PR on GitHub, then runs `pilot resume`.
  The **reconcile step** (deterministic, host-side) checks three things: through
  GitHub's read API, that A's PR is merged; on a fresh clone of the default branch, that
  A's tasks are 100% checked; and that, for every path the graded attempt changed, the
  file on the default branch matches the graded head. This works for merge, squash or
  rebase merges. A mismatch (someone edited after grading) blocks the proposal. It then **proposes** the roadmap edit `A: planned → verified` as a diff and asks
  the operator `y/N`. On `y`, the orchestrator commits and pushes that one-line status
  edit to the fixture's default branch **with the operator's own git credentials on the
  host**. It then re-runs the gate for B from a fresh clone.
- **Rationale:** Constitution V: status edits are applied after human approval, by the
  human's authority. It is not a PR, so it does not count against "exactly 2 PRs", and
  no worker, grader or publisher credential is used. spec-status `reconcile` is an agent
  skill. The pilot uses a deterministic equivalent with the same propose-then-approve
  shape.
- **`reset-fixture`:** an explicit operator command that force-resets the throwaway
  repo's default branch to the fixture template and closes open `pilot/*` PRs. It is
  destructive by design, works only on the configured throwaway repo, and refuses
  (exit 3) unless the repo name ends in `-pilot-fixture` and differs from specfoundry's
  own `origin`.
- **Alternatives considered:** Having the publisher push the status edit, which would
  give the publisher a second PR or a direct-push right it doesn't need. Unblocking on
  the grade alone, which the operator rejected at spec time.

## R10 — Images and pinning (FR-022, S6)

- **Decision:** Three images, each built from a digest-pinned Debian bookworm-slim or
  Alpine base, with exact package versions:
  - `pilot-worker`: git + OpenCode v2.2.7 binary (sha256 above) + entrypoint. Non-root
    uid 10001, no sudo.
  - `pilot-tools`: git, python3, curl, and the spec 0.2.0 binary (sha256 recorded).
    Used by the grader and publisher.
  - `pilot-egress`: tinyproxy.
  They are pushed to a **local registry** container (`registry:2`, digest-pinned) joined
  to the kind network, and pods reference them **only by `@sha256:` digest**.
  Calico v3.29.3, kind v0.27.0 and kubectl v1.32.2 are pinned exactly as in 001.
- **Rationale:** Images loaded with `kind load` have no registry digest, so a pod could
  not pin them by digest. The local-registry pattern is kind's documented approach.
- **Verify at implement:** resolve and record each base image's digest; the
  `registry:2` digest.
- **Resolved 2026-11-13 (T004):** digests are recorded in `pilot/pins.env`
  (`registry:2`, `debian:bookworm-slim`, `alpine:3.20`). The host `spec` binary is
  statically linked (Go), sha256 `29420054…c966`.

## R11 — Orchestrator language and structure

- **Decision:** Python 3.12, **standard library only**, calling `kubectl`, `git`,
  `spec` and `gh` (read-only use: merge status and PR listing) as subprocesses. Bash for
  image entrypoints. The runner is behind a small interface (`runner/base.py`) with one
  backend (`runner/jobs.py`), so 003 can add `runner/kelos.py` without touching the
  gate, grader, publisher or evidence code (constitution VI, PRD F10).
- **Rationale:** Same toolchain as 001 (bash + python3), no dependency installation, and
  every external action is a visible CLI call.
- **Alternatives considered:** Go (matches spec-status, but adds a build step for a
  pilot). The Kubernetes Python client (a dependency to install, and hides the calls).

## R12 — Evidence record and audit (FR-020, SC-004, SC-007)

- **Decision:** `specs/002-m1-gated-pilot/evidence/<run-id>/` holds:
  - `events.jsonl` (an append-only, ordered log of every stage transition)
  - `gate/*.json` (each decision with the raw spec-status JSON snapshot)
  - `attempts/<task>-<n>/` (rendered manifests, `report.json`, `grade.json`, harness
    log tail, spend)
  - `prs.json`, `reconcile/*.json`
  - `checks/results.jsonl` (isolation and credential checks run live against each unit,
    in the 001 style)
  - `teardown.jsonl`, `versions.txt`, `summary.md`
  A final **redaction scan** fails the run if any file matches credential patterns
  (`github_pat_`, `ghp_`, `gho_`, `sk-`, `Bearer `). It also runs `grep -rF -f <(cut -d= -f2-
  <secret env file>)`, so the exact secret values are matched
  without the orchestrator ever loading them into its own memory or logs.
- **Rationale:** A reviewer can answer every Story 3 question from files alone. Order
  is provable from `events.jsonl` (SC-002).
