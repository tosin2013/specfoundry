# PRD: Roadmap-to-Release SDLC on Kubernetes (working name: specfoundry)

Status: DRAFT · Owner: specfoundry maintainers · Date: 2026-11-12 (MST)
Name is a placeholder, not decided.

## 1. Problem

Spec Kit gives us a constitution, specs, plans, tasks and a roadmap. But taking a roadmap row all the way to shipped software is still manual and fragile:

- Workers sharing a single Docker container don't isolate well, and that isn't enough to scale to several workers.
- Nothing stops a worker from starting a task whose dependencies aren't verified.
- "Done" often means CI passed, not that the evidence shows the work is done (dry run, reconciliation, security, functional test, teardown).
- Roadmap status drifts from reality. Issues, PRs and the roadmap aren't tied together.
- Agent runners like Kelos run a prompt in a pod, but they don't own the lifecycle around it, and they give the agent the GitHub token.

## 2. Vision

Take a Spec Kit roadmap end to end through the SDLC. A human approves the roadmap. The system carries each item through spec, plan, tasks, issues, isolated build, independent verification and a draft PR. The human merges, and the roadmap is marked verified only when the evidence supports it, which unblocks the next item. The roadmap is always the source of truth.

Pod runners (plain Kubernetes Jobs now, OpenShift next) are a pluggable build engine, not the product.

## 3. Users

- **Primary:** a solo or small-team developer and infrastructure engineer who uses a frontier controller model (Claude Code, Cursor, Codex) and cheaper worker harnesses (OpenCode and others).
- **Secondary:** teams already on Spec Kit who want governed, auditable agentic delivery on Kubernetes or OpenShift.

## 4. Lifecycle (in scope)

1. **Plan:** constitution check, then spec, clarify, plan and tasks with Spec Kit. This can run **outside the cluster** (a laptop controller) or **inside it** (a planning Job). The handoff is the same either way: the artifacts are committed and the roadmap row is recorded.
2. **Issues:** `/speckit.taskstoissues` creates one GitHub issue per task, linked to the roadmap item. Labels mirror state: ready, blocked, in-progress, verified.
3. **Ready gate:** `spec status` (deterministic CLI, no agent) decides whether an item or issue may start. Blocked items never start.
4. **Route:** an AI rates the item's risk and suggests a mode. Low risk gets a Ralph loop. Medium risk gets a loop with human review after each story. High risk is built step by step. A human confirms before any loop is staged, and the system never starts a loop on its own.
5. **Build:** one isolated unit per worker (its own pod and namespace), with a thin keyless harness image (OpenCode first; Claude Code, Codex and Copilot later), a NetworkPolicy, a ResourceQuota, a deadline, and a service account with token automount off. The worker emits a git bundle plus a report.
6. **Verify:** an independent grader in a separate namespace runs the evidence ladder and spec-status `verify-readiness` (report-only mode).
7. **Ship:** a publisher Job, the only holder of GitHub write credentials, opens one draft PR (`Closes #N`) with the evidence in the body. A human merges. Release follows the repo's normal process.
8. **Close the loop:** after merge, `reconcile` proposes moving the item to verified, the issue closes, and the next items unblock.

## 5. Requirements

### Functional

- F1: Read the Spec Kit roadmap (speckit-roadmap format) and spec-status JSON (schema 1.0) as the only scheduling inputs.
- F2: Planning location is configurable per project: `local` or `in-cluster`.
- F3: Create and update GitHub issues from tasks. Keep labels in sync with spec-status state.
- F4: The gate fails closed when an item is blocked (see spec-status issue 2). Until that ships, read `summary.blocked_count` and `dependencies[].satisfied`.
- F5: Risk rating and mode suggestion per item, recorded alongside the run. Human confirmation is required before a loop.
- F6: Per-project setting for who launches workers: the human, or the controller after scope approval. Ask when it's unset and remember the answer.
- F7: Loop caps map to deadlines and retry limits. Every run respects a spend cap.
- F8: One draft PR per item or task. Never auto-merge.
- F9: Every run writes an evidence record (inputs, image digests, gate result, grader report, PR link) that can be audited later.
- F10: Pluggable runner. Plain Kubernetes Jobs first; OpenShift next. Agent runners such as Kelos are competitors and references, not dependencies.
- F11: Pluggable SCM. GitHub first; Bitbucket later.

### Security and isolation (non-negotiable)

- S1: Never two workers in one container. One unit (pod and namespace) per worker.
- S2: Workers never hold GitHub or SCM credentials. Only the publisher does.
- S3: The controller never holds the worker's model key. Worker keys are per-run Secrets with spend caps.
- S4: Egress allowlist via NetworkPolicy (needs Calico or Cilium; kind's default CNI doesn't enforce it).
- S5: The grader can't be written to by the worker. Answer keys and grading material are never mounted in the worker.
- S6: Images are thin, non-root, with no sudo, pinned by digest.

### Non-functional

- N1: Works on kind (single machine, about 8 GB free), on any approved machine (Mac, Ubuntu, CI), and on OpenShift, including its restricted SCC (arbitrary UID), mirrored or air-gapped registries, and HTTP proxies.
- N2: Harness- and host-agnostic docs with minimal governance.
- N3: Repeatable: one command stands up the stack, and teardown is verified.
- N4: Telemetry is operator observability only (metrics, traces and events to an operator-run collector); no phone-home.

## 6. Build on, don't rebuild

- **spec-status** (owned): CLI gate plus v0.2.0 skills (review, explain, reconcile, unblock, verify-readiness).
- **Spec Kit:** planning commands and `taskstoissues`.
- **Kelos (reference, not a dependency):** ideas such as its agent-image contract and spend budgets may inform our design, with attribution.
- **OpenShift validation skills:** OpenShift, Helm, GitOps and validation skills for the evidence ladder.
- **Process playbooks:** the human-facing process docs.

## 7. Out of scope (v1)

- Auto-merge, or any merge without a human.
- Building a general-purpose agent runner. specfoundry competes on governed, least-privilege delivery, not on runner features.
- Hosted SaaS or a UI. CLI, CRDs and GitHub are the interface.
- Publishing official agent images for every harness. We recommend images rather than maintain them, except for one reference thin OpenCode image.

## 8. Dependencies on spec-status (draft issues, not opened)

1. Report-only mode for the skills (headless worker and grader).
2. Per-item readiness check that exits non-zero when blocked.
3. Minimal published container image of the CLI.

## 9. Milestones

- **M0 (done 2026-11-12):** stub isolation test on kind with Calico, 32 of 33 pass. Kelos read-only review done.
- **M1 Pilot:** Codex's two-task pilot. Task A's grade fails, so task B stays blocked. A is retried and passes, then B runs. Exactly one draft PR per task. Runs on kind with plain Jobs.
- **M2 Hardened images and competitive review:** GitHub-built, digest-pinned images for laptops and enterprise; a factual Kelos comparison.
- **M3 GitHub loop:** taskstoissues, label sync, PR `Closes #N`, reconcile after merge.
- **M4 Planning in-cluster** (optional) **plus OpenShift** target.

## 10. Success metrics

- No worker ever starts on a blocked item (pilot proves it).
- 100% of PRs come from the publisher. No worker has a credential (verified by an audit of the evidence record).
- Roadmap status matches merged reality after each cycle (reconcile shows no drift).
- Stack up to first draft PR on a fresh kind cluster within one documented command sequence.

## 11. Open questions

- Q1: Final project name and repo location (new repo vs. inside spec-status org).
- Q2 (resolved 2026-11-13): Kelos is a competitor; neither wrapped nor forked.
- Q3: Which machine runs M1 and M2 (Ubuntu box, Mac, another lab machine)? One candidate machine can't run cert-manager because its ClusterIP and DNS don't work there.
- Q4: Granularity: one worker run per roadmap item, or per task or issue?
- Q5: Worker model provider and spend cap defaults (OpenCode Go plan, DeepSeek, others).
