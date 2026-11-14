<!--
SYNC IMPACT REPORT
==================
Version change: 1.5.0 → 1.6.0
Bump rationale: MINOR — a new planned spec (011), a new constraint (C-11), a new open
question (Q7), and material scope changes to 004 and 005.

Changes this revision (owner decisions 2026-11-14, from the 006 fresh-machine validation
discussion):
  - New C-11: two modes, one set of guarantees. Laptop mode (operator off): the CLI
    orchestrates. Cluster mode (operator on): the CLI is a client of an in-cluster operator.
    Human approvals can be given on GitHub in both modes; publisher credentials may be a
    fine-grained token or a GitHub App in either mode
  - New entry: 011 Cluster mode: specfoundry Kubernetes operator
  - 004: GitHub approvals for the human decisions (both modes) added to scope; the publisher
    credential note changes from "replace the token with a GitHub App" to "support both,
    chosen per install" (old text struck through)
  - 005: note that a remote OpenShift cluster is first driven by the laptop CLI (configurable
    kube context, preflight instead of cluster creation, namespace permissions); in-cluster
    orchestration is 011
  - New Q7: product name and CLI interface ("pilot" is a prototype name)
  - Cross-cutting: 007, 009 and 010 run in the operator in cluster mode

Specs affected: 004, 005, 011 (new); 007, 009, 010 (note only)
Open questions added/resolved: Q7 added

Previous revision 1.5.0 (2026-11-13):
Version change: 1.4.0 → 1.5.0
Bump rationale: MINOR — four new planned specs (007–010) and an open question resolved,
plus a status transition (003 → verified) and wording updates.

Changes this revision (from debrief specs/003-m2-kelos-backend/roadmap-reviews/
debrief-20261113T182000Z.md; owner decisions 2026-11-13):
  - Status: 003 planned → verified (validation run 20261113T180203Z on GHCR images: checks
    32/32, audit 11/11, teardown 3/3; CI and enterprise evidence; evidence merged to main via
    PR #3); spec dir linked
  - 003 scope wording and C-09: digests live in pilot/images.lock (outputs, never a workflow
    trigger); pilot/pins.env holds inputs
  - New entries: 007 Operator observability (closes Q6), 008 More harnesses, 009 Period
    spend budget at the gate, 010 Event-proposed runs
  - Per-run provider keys: revisited in 003 with no change; carried to 005
  - Notes: 004 (GitHub Actions PR permission; public-repo permissions field), 005
    (per-run keys; explicit podFailurePolicy candidate), Q1 (public, Apache-2.0)

Specs affected: 003, 004, 005, 007, 008, 009, 010
Open questions added/resolved: Q6 resolved (→ 007)

Previous revision 1.4.0 (2026-11-13):
Version change: 1.3.0 → 1.4.0
Bump rationale: MINOR — material scope change to 003 (renamed: Kelos runner work dropped),
C-05 reworded, a new constraint (C-10 telemetry), a new end state, and a new open question.

Changes this revision (owner decision 2026-11-13; constitution amended to 1.1.0 the same day):
  - Positioning: Kelos is a competitor and design reference, not a dependency or runner
    (constitution VI). Target environments: laptops and enterprise (constitution VII)
  - C-05 reworded accordingly; Kelos runner adoption removed
  - 003 renamed "M2 hardened images and Kelos competitive review"; scope: GitHub-built
    digest-pinned images (laptop and enterprise ready) plus a factual competitive review
    (security bar comparison and a gap list of Kelos features enterprises expect)
  - New C-10: first-party telemetry is operator observability only; no phone-home
  - New end state: runs on laptops and in enterprise environments
  - New Q6: which spec delivers operator observability (C-10)
  - Cross-cutting: PRD F10 drift noted, then resolved the same day (PRD updated by the owner's approval)

Specs affected: 003 (and 005 via C-10)
Open questions added/resolved: Q6 added

Previous revision 1.3.0 (2026-11-13):
Version change: 1.2.0 → 1.3.0
Bump rationale: MINOR — material scope change to 003, an amended constraint (C-05) and a new
constraint (C-09), plus a note on 005.

Changes this revision (owner decision 2026-11-13, after reading Kelos v0.64.0's source during
003 planning: security first):
  - C-05 amended: wrap Kelos, never fork; if Kelos cannot meet the security bar by
    configuration alone, do not adopt it (plain Jobs stays the runner; Kelos is a reference)
  - New C-09: pilot images built by GitHub Actions from verified upstream sources, published
    to a public registry per target platform (GHCR for kind; possibly Quay variants for
    OpenShift), referenced only by digest
  - Scope changed on 003: assess Kelos against a security bar with a possible `do-not-adopt`
    outcome; forking Kelos is out of scope; GitHub-built images added; outcome reworded
  - Note added on 005: decide OpenShift image variants on Quay vs mirroring the C-09 images

Specs affected: 003, 005
Open questions added/resolved: Q2 resolved (wrap or do not adopt; never fork)

Previous revision 1.2.0 (2026-11-13):
Version change: 1.1.0 → 1.2.0
Bump rationale: MINOR — new constraints (C-07, C-08), a new planned spec (006) and a
material scope change on 003, plus a status transition on 002.

Changes this revision (from debrief specs/002-m1-gated-pilot/roadmap-reviews/
debrief-20261113T032500Z.md, approved by the owner 2026-11-13):
  - Status: 002 planned → verified (pilot run 20261113T030655Z: checks 32/32, audit
    11/11, teardown 3/3, mutation test caught all; spec dir linked)
  - New constraints: C-07 (egress through per-role domain-allowlist proxies), C-08 (no
    worker-writable storage shared with the grader; results via framed logs)
  - Scope changed on 003: adds the Kelos adapter implementing runner/base.py and keeping
    C-07/C-08, and pinning plus checking the Calico manifest sha256
  - Note added on 004: GitHub App with per-run installation tokens for the publisher
  - New entry: 006 Operator guide (planned, depends on 002)
  - Open questions: Q3 decided for M1 (open for M2); Q4 decided for the pilot; Q5 partly
    decided
  - Cross-cutting notes: accepted per-run-key deviation; 002 workarounds for the
    spec-status asks

Specs affected: 002, 003, 004, 006
Open questions added/resolved: Q3 partly resolved (M1), Q4 resolved for M1, Q5 partly resolved

Previous revision 1.1.0 (2026-11-13):
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR — material scope change (Kelos read-only review moved from 001 to 003)
plus a status transition.

Changes this revision:
  - Status: 001 implemented → verified (rebuilt suite test/isolation/run.sh, 37/37 pass,
    evidence specs/001-m0-isolation-stub/evidence/20261113T014128Z, teardown verified)
  - Scope changed on 001: Kelos read-only review removed (no written review in repo)
  - Scope changed on 003: Kelos read-only review added as a required input to C-05

Specs affected: 001, 003
Open questions added/resolved: none

Notes: the original 2026-11-12 M0 run (32/33) was on another machine and is not
reproducible here; the rebuilt suite replaces it. Owner approved the move on 2026-11-13.

Previous revision 1.0.0 (2026-11-13): initial creation from docs/prd.md, entries 001–005,
decisions C-01 … C-06, open questions Q1–Q5.
-->

# specfoundry — Spec Roadmap

Living, non-binding map of the specs planned for specfoundry. It is **not a
commitment to order or scope** — it captures the spec-specific discussion,
decisions, technology choices, outcomes, and constraints surfaced during the
constitution and grilling phases so they are not lost before the spec that needs
them is written. Specs are scoped and clarified when they are actually started.
Foundations: the project [constitution](constitution.md) and the
[PRD](../../docs/prd.md).

Status legend (lifecycle): **undecided** · **needs-info** · **planned** ·
**specced** · **in-progress** · **implemented** · **verified** · **deferred** ·
**abandoned**.

---

## Vision & End States

- A human-approved Spec Kit roadmap is carried end to end: spec, plan, tasks,
  issues, isolated build, independent verification, draft PR, human merge.
- A roadmap entry becomes `verified` only when the evidence supports it, and that
  is what unblocks the next entry.
- No worker ever starts on a blocked item, and no worker ever holds an SCM
  credential (auditable from evidence records).
- From a fresh kind cluster to the first draft PR in one documented command
  sequence, with verified teardown.
- The same governed pilot runs on a laptop (kind) and in an enterprise environment
  (OpenShift restricted SCC, arbitrary UID, mirrored or air-gapped registries, proxies),
  with a small trust base and audit evidence a security team can review.

## Constraints & Decisions

- **C-01 — Scheduling inputs:** only the roadmap and `spec status` JSON (schema
  1.0) schedule work (PRD F1, constitution I).
- **C-02 — Gate fails closed:** blocked or unevaluable means no start. Until
  spec-status ships a per-item readiness exit code, read `summary.blocked_count`
  and `dependencies[].satisfied` (PRD F4, constitution II).
- **C-03 — Isolation and credentials:** one worker per pod and namespace; only the
  publisher holds SCM write credentials; grader is separate and not writable by
  workers (PRD S1–S6, constitution IV).
- **C-04 — Human merge only:** draft PRs only, one per item or task, never
  auto-merge (PRD F8, constitution V).
- **C-05 — ~~Wrap Kelos, don't fork~~ Kelos is a competitor, not a dependency:**
  ~~fork only if token split, bundle-out or stage retry cannot be worked around (PRD Q2
  default, constitution VI).~~ ~~**Amended 2026-11-13:** never fork. Kelos is adopted as a
  runner only if it meets the security bar (spec 003) through configuration alone.
  Otherwise it is not adopted: plain Jobs remains the runner and Kelos is used as a
  reference only (constitution II, IV, VI).~~ **Amended again 2026-11-13 (constitution
  1.1.0):** Kelos is a competitor and design reference. It is not adopted as a runner or
  forked. Its ideas may be borrowed, with Apache-2.0 licence and NOTICE kept for any copied
  code. Public comparisons stay factual. Plain Jobs is the runner now and OpenShift next.
- **C-06 — Enforcing CNI:** isolation tests run on Calico or Cilium; kind's
  default CNI does not enforce NetworkPolicy (PRD S4).
- **C-07 — Egress through per-role allowlist proxies:** worker and publisher egress
  goes only through a domain-allowlisting proxy for their role (model hosts for
  workers, the SCM for the publisher). NetworkPolicy decides which namespace may reach
  which proxy, because Calico OSS cannot match domain names. A worker can never reach
  the SCM proxy (PRD S2, S4; decided in 002, research R4).
- **C-08 — No storage shared between worker and grader:** nothing writable is shared
  between a worker and the grader. Worker results leave only as a framed stdout result
  collected by the orchestrator; grading material lives only in grader namespaces (PRD
  S5; decided in 002, research R5).
- **C-09 — Images built in GitHub, pinned by digest:** pilot images are built by GitHub
  Actions from verified upstream sources (never an operator's local binary), contain no
  secrets, are published to a public registry chosen per target platform, and are
  referenced only by digest. Digests live in `pilot/images.lock` (written only by the
  image workflow's PR and never a workflow trigger); build inputs live in `pilot/pins.env`.
  kind and local runs use GHCR (`ghcr.io/tosin2013/
  specfoundry-*`). The OpenShift target may use different images published to Quay (for
  example UBI-based variants for OpenShift's arbitrary-UID restricted SCC); 005 decides
  (PRD S6, constitution VII; decided 2026-11-13).
- **C-10 — Telemetry is operator observability only:** no third-party telemetry. First-party
  telemetry means metrics, traces and events (e.g. OpenTelemetry or Prometheus) sent only to
  a collector the operator runs. Nothing leaves the operator's environment unless they
  configure it; no phone-home usage telemetry; never secrets, prompts or source code
  (constitution Security & Isolation Constraints, 1.1.0).
- **C-11 — Two modes, one set of guarantees:** *laptop mode* (operator off): the CLI runs the
  orchestration itself against a local or remote cluster. *Cluster mode* (operator on): the
  CLI is a client of the specfoundry Kubernetes operator running in the cluster. The CLI
  detects which applies, or the operator chooses it in configuration. Both modes keep C-01
  to C-10, produce the same evidence and pass the same audit; cluster mode adds features and
  never relaxes a guarantee. The human decisions (mode confirmation, retries, merge, approving
  a status change) can be given on GitHub in both modes; terminal prompts stay available in
  laptop mode. The publisher's SCM credential may be a fine-grained token or a GitHub App
  (per-run installation tokens) in either mode; the same checks apply to both (decided
  2026-11-14).

## Planned Specs

### 001 — M0 stub isolation test on kind with Calico  [status: verified]

- **Description:** Stub worker isolation test suite on kind with Calico.
- **Outcome:** All isolation checks pass on kind with Calico, the evidence is
  recorded in the repo, and teardown is verified.
- **Scope (in):** kind cluster with Calico, namespace/NetworkPolicy/ResourceQuota/
  service-account checks for a stub worker.
- **Scope (out):** real harness images, grader, publisher, GitHub integration, Kelos
  review (moved to 003).
- **Depends on:** none
- **Governed by:** C-03, C-06
- **Addresses:** docs/prd.md §9 M0
- **Spec dir:** specs/001-m0-isolation-stub
- **Notes:** First run 2026-11-12 on another machine passed 32 of 33. Rebuilt
  here as test/isolation/run.sh; verified 2026-11-13 with 37 of 37 checks passing
  (including teardown), control probes for every blocked path, and a mutation test.
  Evidence: specs/001-m0-isolation-stub/evidence/20261113T014128Z.

### 002 — M1 pilot: two-task gate on kind with plain Jobs  [status: verified]

- **Description:** Codex's two-task pilot run with plain Kubernetes Jobs.
- **Outcome:** Task A's grade fails so task B stays blocked; A is retried and
  passes, then B runs; exactly one draft PR per task, opened by the publisher.
- **Scope (in):** gate stage using spec status, plain-Jobs runner, isolated worker
  namespace, separate grader, publisher Job, evidence record per run.
- **Scope (out):** Kelos, GitHub issue sync, in-cluster planning, OpenShift.
- **Depends on:** 001
- **Governed by:** C-01, C-02, C-03, C-04
- **Addresses:** docs/prd.md §9 M1, §10 first two metrics
- **Spec dir:** specs/002-m1-gated-pilot
- **Notes:** Proves the "no worker starts on a blocked item" metric. ~~Machine
  choice is open (Q3).~~ Ran on the Ubuntu host (31 GB, 8 CPUs), kind + Calico; one
  worker run per roadmap item (Q4 for M1). Verified 2026-11-13, run
  20261113T030655Z: A/1 failed grading (induced), B stayed refused, A/2 passed, draft
  PR #1 merged by the owner, reconcile approved, B passed, draft PR #2. Checks 32/32,
  audit 11/11, teardown 3/3, mutation test caught all. Evidence:
  specs/002-m1-gated-pilot/evidence/20261113T030655Z. Known limits are in the 002 plan.

### 003 — M2 hardened images and Kelos competitive review  [status: verified]

- **Description:** Build the pilot's images in GitHub so they run on laptops and in
  enterprise environments, and write a factual competitive review of Kelos.
- **Outcome:** GitHub Actions builds the worker (OpenCode from a checksum-verified upstream
  release), tools and egress images, publishes them as public digest-pinned images, and
  `pilot up` pulls them by digest; a plain-Jobs pilot run on those images passes its full
  audit. A written review compares Kelos v0.64.0 with specfoundry against the security bar,
  and lists the Kelos features enterprises expect, as candidate roadmap items.
- **Scope (in):** image workflow (registry as a parameter; GHCR now); arbitrary-UID-friendly,
  non-root, no-sudo images with no secrets; digest PRs to ~~`pilot/pins.env`~~ `pilot/images.lock`; pull-by-digest
  `pilot up` with `--local-build` fallback; Calico manifest hash pinned and checked;
  competitive review (security bar SB-1–SB-8 comparison, enterprise gap list); optional
  Kelos-compatible entrypoint in the worker image so Kelos users can run it.
- **Scope (out):** Kelos runner adapter or install; forking Kelos; other harness images;
  OpenShift (005); operator observability (see Q6).
- **Depends on:** 002
- **Governed by:** C-03, C-05, C-07, C-08, C-09, C-10
- **Addresses:** docs/prd.md §9 M2 (re-scoped), S6, N1, N3
- **Spec dir:** specs/003-m2-kelos-backend
- **Notes:** Renamed from "M2 Kelos backend" on 2026-11-13. Revisit per-run provider keys
  here (see Cross-Cutting Notes): revisited 2026-11-13, no change (Kelos uses a static
  key Secret too); carried to 005. Verified 2026-11-13: validation run 20261113T180203Z on
  the GHCR images (checks 32/32, audit 11/11, teardown 3/3, `image_source: pinned`);
  images public with provenance and SBOM; no rebuild loop; arbitrary-UID and mirror checks
  pass. Evidence: specs/003-m2-kelos-backend/evidence/. Superseded entry text (roadmap 1.3.0), kept for history:
  ~~(former description) ~~Run the M1 pilot through Kelos behind an adapter.~~ Assess Kelos~~
  ~~against the security bar and adopt it as the worker runner only if it meets the bar by~~
  ~~configuration; build the pilot's images in GitHub.~~
  ~~(former outcome) ~~Same pilot result as 002 with Kelos as the runner: namespace,~~
  ~~policies, thin image, gate stage, publisher and separate grader all preserved.~~ A~~
  ~~written review scores Kelos against the security bar and records `wrap`,~~
  ~~`wrap-with-workarounds` or `do-not-adopt`. If adopted, the 002 pilot result is~~
  ~~reproduced with Kelos running the workers (gate, publisher and separate grader~~
  ~~preserved). If not, plain Jobs stays the runner. Either way, the pilot's images are~~
  ~~built by GitHub Actions and pulled by digest (C-09).~~
  ~~(former scope (in)) written read-only Kelos review (security model, token handling,~~
  ~~bundle-out, stage retry) as the input to C-05; Kelos adapter; pinned Kelos version~~
  ~~with telemetry off; thin OpenCode reference image pinned by digest; the Kelos~~
  ~~adapter implements the 002 runner interface (`pilot/specfoundry_pilot/runner/base.py`)~~
  ~~and keeps C-07 and C-08; pin and check the Calico manifest sha256~~
  ~~(`CALICO_SHA256` in `pilot/pins.env`, checked by `pilot up`). Added 2026-11-13: the~~
  ~~security bar (no SCM credential in workers, no sudo, no automatic retries, telemetry off,~~
  ~~digest pins, effective token off, C-07/C-08 kept, controller privileges reviewed and~~
  ~~accepted); the Kelos adapter only if the review adopts; GitHub Actions building~~
  ~~`pilot-worker` (OpenCode from a verified upstream release), `pilot-tools` and~~
  ~~`pilot-egress` to public GHCR, with `pilot up` pulling by digest.~~
  ~~(former scope (out)) other harness images, OpenShift, **forking Kelos** (C-05).~~
  ~~(former dependency) 002~~
  ~~(former governed by) C-03, C-05, C-07, C-08, C-09~~
  ~~(former notes) Revisit per-run provider keys here (see Cross-Cutting Notes).~~
  ~~(former addresses) docs/prd.md §9 M2, F10~~

### 004 — M3 GitHub loop  [status: planned]

- **Description:** Tie roadmap entries, issues and PRs together on GitHub.
- **Outcome:** taskstoissues creates one issue per task, labels mirror spec status
  state, PRs carry Closes #N, and reconcile after merge shows no drift.
- **Scope (in):** issue creation, label sync, PR linking, post-merge reconcile. Added
  2026-11-14: GitHub approvals for the human decisions (mode, retry, approving a status
  change; merge is already on GitHub), usable in laptop and cluster mode (C-11); GitHub App
  as a second publisher credential beside the fine-grained token, with setup docs and checks.
- **Scope (out):** Bitbucket and other SCMs.
- **Depends on:** 003
- **Governed by:** C-01, C-04, C-11
- **Addresses:** docs/prd.md §9 M3, F3, F11
- **Notes:** ~~Replace the publisher's fine-grained token with a GitHub App that mints a
  1-hour installation token per run, scoped to the target repo, so PRs show
  `<app>[bot]` rather than the owner's account.~~ **Amended 2026-11-14: support both,
  chosen per install.** The fine-grained token stays the default (simplest; PRs show the
  owner's account). The GitHub App mints a 1-hour installation token per run, requested for
  the target repo only with contents and pull-request write, so PRs show `<app>[bot]`; it is
  recommended for teams and cluster mode, not required. In laptop mode the App's private key
  stays on the host and only the short-lived token enters the cluster. Both pass the same
  write probe (fixture writable, canary not) and P09. In 002 the token owner is the operator,
  which weakens PRD §10 metric 2 as seen from GitHub (the evidence audit still shows the
  publisher Job opened every PR). Learned in 003: new repositories block GitHub Actions
  from opening PRs until *Allow GitHub Actions to create and approve pull requests* is
  enabled; on a public repository the `permissions` field of `GET /repos` reports the
  account's rights, not a fine-grained token's (use a write probe instead).

### 005 — M4 in-cluster planning and OpenShift target  [status: planned]

- **Description:** Optional in-cluster planning Job, and OpenShift as a target
  platform.
- **Outcome:** Planning location is configurable per project (local or
  in-cluster) with the same handoff, and the pilot runs on OpenShift.
- **Scope (in):** planning Job, per-project planning setting, OpenShift runner
  validation.
- **Scope (out):** hosted SaaS or UI.
- **Depends on:** 003
- **Addresses:** docs/prd.md §9 M4, F2, N1
- **Notes:** In-cluster planning is optional per the PRD; OpenShift is the
  required part. Decide whether OpenShift needs its own image variants (for example UBI
  base, arbitrary-UID support) published to Quay, or the C-09 images mirrored there; the
  003 image workflow takes the registry as a parameter (003 showed the images already run
  as an arbitrary UID and mirror by digest). Revisit per-run provider keys here (carried
  from 003; enterprise secret managers may make them practical). Candidate: an explicit
  `podFailurePolicy` on worker Jobs, so infrastructure disruptions are recorded distinctly
  from worker failures (from the 003 Kelos review). Added 2026-11-14: first prove the laptop
  CLI against a remote OpenShift cluster (C-11 laptop mode): a configurable kube context
  instead of the hard-coded kind context, preflight checks instead of creating a cluster,
  and enterprise namespace permissions (users often cannot create namespaces).
  Orchestration inside the cluster is 011.

### 006 — Operator guide: repeat the pilot from zero  [status: planned]

- **Description:** End-user documentation so someone new can repeat the governed
  pilot on their own machine.
- **Outcome:** Someone new, starting from a fresh machine and using only the guide,
  stands up the stack, runs the pilot through both human gates, tears down, and gets a
  passing audit.
- **Scope (in):** prerequisites and machine sizing; provider setup (OpenCode config
  directory, `{file:}` key reference); publisher token creation and
  `pilot publisher-token`; the command sequence with every prompt; the merge pause;
  reading the evidence and audit; teardown; troubleshooting from 002's real failures;
  where 003 (Kelos) and 004 (GitHub App) will change the steps.
- **Scope (out):** hosted docs site or UI; naming specific private model providers.
- **Depends on:** 002
- **Governed by:** C-07
- **Addresses:** constitution VII ("one documented command sequence"), docs/prd.md N2, N3
- **Notes:** Requested by the owner 2026-11-13. Use run 20261113T030655Z as the
  worked example.

### 007 — Operator observability  [status: planned]

- **Description:** Metrics, traces and events that operators can use to watch and audit
  pilot runs in their own environment.
- **Outcome:** Gate decisions, attempts, spend and run duration are emitted as metrics,
  traces and events (OpenTelemetry/Prometheus) to an operator-run collector. Nothing leaves
  the environment unless configured, and evidence and telemetry carry no secrets, prompts
  or code.
- **Scope (in):** instrumentation of the gate, attempts, grading, publishing and spend; an
  export to an operator-configured collector; documentation.
- **Scope (out):** phone-home or vendor-hosted telemetry; dashboards as a product.
- **Depends on:** 002
- **Governed by:** C-10
- **Addresses:** constitution Security & Isolation Constraints (telemetry); docs/prd.md N4
- **Notes:** Proposed in the 003 Kelos review; closes Q6 (owner decision 2026-11-13).

### 008 — More harnesses (Claude Code, Codex)  [status: planned]

- **Description:** Additional worker harnesses behind the same worker contract.
- **Outcome:** Each harness ships as a thin, digest-pinned, no-sudo worker image built by
  the `pilot-images` workflow, behind the same worker contract; a pilot run with each
  passes its full audit.
- **Scope (in):** Claude Code and Codex worker images; per-harness configuration docs;
  spend accounting from each harness's usage output.
- **Scope (out):** other harnesses; harness-specific features outside the worker contract.
- **Depends on:** 003
- **Governed by:** C-03, C-07, C-09
- **Addresses:** docs/prd.md §2 (harness-agnostic), N2
- **Notes:** Proposed in the 003 Kelos review (owner decision 2026-11-13).

### 009 — Period spend budget at the gate  [status: planned]

- **Description:** A spend limit per day or per project, enforced before work starts.
- **Outcome:** A daily or project spend limit is checked at the gate before any worker
  starts, fails closed when exceeded or unevaluable, and is recorded in the evidence; it
  adds to the per-attempt cap rather than replacing it.
- **Scope (in):** budget configuration; spend accounting across runs; gate integration;
  evidence fields.
- **Scope (out):** provider billing integrations.
- **Depends on:** 002
- **Governed by:** C-01, C-02
- **Addresses:** docs/prd.md F7
- **Notes:** Idea borrowed from Kelos's admission-time TaskBudget (attributed in the 003
  review; owner decision 2026-11-13).

### 010 — Event-proposed runs  [status: planned]

- **Description:** Let authenticated external events propose work without bypassing
  governance.
- **Outcome:** Authenticated events (for example signed webhooks or an issue label) may
  *propose* a roadmap item for a run; the spec-status gate and a human mode confirmation
  still decide.
- **Scope (in):** event authentication; proposal recording; handoff to the gate and the
  mode confirmation.
- **Scope (out):** automatic runs without human confirmation; unauthenticated endpoints.
- **Depends on:** 004
- **Governed by:** C-01, C-02, C-04
- **Addresses:** docs/prd.md F6
- **Notes:** Proposed in the 003 Kelos review (owner decision 2026-11-13).

### 011 — Cluster mode: specfoundry Kubernetes operator  [status: planned]

- **Description:** An in-cluster operator runs governed runs, with the CLI as its client
  (operator on); the CLI still works standalone (operator off).
- **Outcome:** The operator runs governed runs inside the cluster under its own scoped
  service account, with human approvals on GitHub. The CLI works with it (operator on) or
  without it (operator off). A cluster-mode run passes the same full audit as a laptop run.
- **Scope (in):** the operator and a run resource it acts on; the gate as a container in the
  cluster; run state and evidence stored in the cluster; model keys and the publisher
  credential (token or GitHub App key) from cluster secrets or an enterprise secret store,
  with the operator minting per-run App tokens; parallel runs; permissions through
  Kubernetes RBAC; the CLI's operator on/off detection; GitHub approvals (from 004).
- **Scope (out):** a hosted SaaS or UI; multi-cluster; any weakening of a guarantee.
- **Depends on:** 004, 005
- **Governed by:** C-01, C-02, C-03, C-04, C-07, C-08, C-10, C-11
- **Addresses:** docs/prd.md F2, N1, §9 M4
- **Notes:** Owner decision 2026-11-14. 007 (observability), 009 (period budgets) and 010
  (event-proposed runs) gain the most in cluster mode. Decide here how runs get namespaces
  when users cannot create them. Depends on spec-status shipping a CLI container image for
  the in-cluster gate (PRD §8). The GitHub App is the recommended publisher credential here.

## Open Questions

- Q1 — Final project name and repo location (new repo vs. inside the spec-status
  org). Interim home: GitHub repo tosin2013/specfoundry (public since 2026-11-13, Apache-2.0,
  with CONTRIBUTING and a Code of Conduct).
- Q2 — Kelos as wrapped dependency vs. fork (default: wrap, see C-05). **Resolved
  2026-11-13:** never fork; wrap only if the security bar is met by configuration,
  otherwise do not adopt (C-05 amended).
- Q3 — Which machine runs M1 and M2 (Ubuntu box, Mac, another lab machine). **M1 decided
  2026-11-13:** the Ubuntu host (31 GB, 8 CPUs). Still open for M2.
- Q4 — Granularity: one worker run per roadmap entry, or per task or issue. **Decided
  for M1:** one worker run per roadmap item. Revisit in 004, where issues are per task.
- Q5 — Worker model provider and spend cap defaults. **Partly decided 2026-11-13:**
  harness OpenCode 2.2.7; provider is operator configuration (not named in docs); caps
  default to $1 per attempt with a 2M-token fallback when the provider reports no cost.
  Still open: provider choice for shared use, and USD accounting (declaring model
  prices).
- Q6 — Which spec delivers operator observability (C-10): metrics, traces and events for
  gate decisions, attempts, spend and run duration to an operator-run collector? Candidates:
  a new entry after 003, or folded into 004/005. **Resolved 2026-11-13:** entry 007.
- Q7 — Product name and CLI interface: `pilot` is a prototype name, and the CLI becomes
  the interface for humans and LLM agents in both modes (C-11). Decide the name and the
  stable command surface before 011 (raised 2026-11-14).

## Cross-Cutting Notes

- spec-status asks drafted in PRD §8 (report-only skills, per-item readiness exit
  code, CLI container image) gate 002 and 003 in practice; track them as upstream
  issues. **002 workarounds in place:** the gate runs on the host (no CLI image); the
  grader uses `spec status --json` (no report-only `verify-readiness`); reconcile is a
  deterministic pilot step (the skill needs an agent). See the 002 plan, Known limits.
- ~~**PRD drift (2026-11-13):** docs/prd.md F10 ("First backend is Kelos") and §9 M2 still
  describe Kelos as a backend. The owner has been sent replacement text; until the PRD is
  edited, the roadmap and constitution 1.1.0 take precedence.~~ Resolved 2026-11-13: the
  PRD was updated (F10, §6, §7, §9 M2, Q2, N1, new N4).
- **Accepted deviation (002):** constitution IV asks for per-run worker keys with spend
  caps. 002 copies a long-lived provider key into a per-attempt Secret (deleted with the
  attempt) and enforces the cap with the pilot watchdog and deadline. Accepted by the
  owner 2026-11-13; revisit in 003. Revisited in 003 (no better mechanism found, including
  in Kelos); carried to 005.
- **Cluster mode (2026-11-14):** in cluster mode, 007 (observability), 009 (period budgets)
  and 010 (event proposals) run in the operator (011); in laptop mode they run in the CLI,
  where they apply at all. Both modes keep C-11's guarantees.

---

**Version**: 1.6.0 | **Ratified**: 2026-11-13 | **Last Amended**: 2026-11-14
