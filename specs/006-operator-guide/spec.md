# Feature Specification: Operator guide — repeat the pilot from zero

**Feature Branch**: `006-operator-guide`

**Created**: 2026-11-13

**Status**: Draft

**Roadmap**: `.specify/memory/roadmap.md` entry 006 (depends on 002, verified; builds on 003,
verified)

**Input**: User description: "006" — roadmap entry 006: end-user documentation so someone new
can repeat the governed pilot on their own machine.

## Context

specfoundry is now public. Its pilot works, but much of what it takes to run it lives in
evidence files, spec contracts and one long working session. Examples:
- how to lay out the model provider's configuration;
- why a token must be scoped to one repository;
- what each prompt means;
- what to do when the run pauses for a merge;
- how to read the audit;
- the dozen real failures and their fixes.

Constitution VII promises "one documented command sequence" that anyone can repeat, on a
laptop or in an enterprise environment. 006 delivers that for the pilot. It's a guide that
someone who has never seen the project can follow from a fresh machine to a passing audit,
proven by having someone actually do that.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A newcomer completes the pilot using only the guide (Priority: P1)

As someone new to specfoundry, with a suitable machine and accounts but no prior context, I
can follow the guide from start to finish:
- install the prerequisites;
- configure a model provider and a scoped publisher token;
- stand up the stack;
- run the pilot through both human gates;
- tear down;
- see a passing audit.

I never need to read the source code, ask the maintainers, or consult the conversation
history that produced the pilot.

**Why this priority**: This is the roadmap outcome for 006 and the constitution's
repeatability promise.

**Independent Test**: A person who has not run the pilot before follows only the guide on a
fresh machine. Their run succeeds, the final audit passes, and every place they hesitated or
deviated is recorded and fixed in the guide.

**Acceptance Scenarios**:

1. **Given** a fresh machine that meets the stated prerequisites, **When** a newcomer
   follows the guide in order, **Then** they reach a passing audit and verified teardown
   without help.
2. **Given** each prompt the pilot shows (mode confirmation, retry, reconcile approval),
   **When** the newcomer reaches it, **Then** the guide has already explained what it means,
   what to answer, and what happens if they answer "no".
3. **Given** the merge pause, **When** the run stops after task A's PR, **Then** the guide
   tells them exactly what to review, how to merge, and how to resume.
4. **Given** the run finishes, **When** they open the evidence, **Then** the guide explains
   the summary, the audit checks, and the refused-egress log in plain language.

---

### User Story 2 - When something goes wrong, the guide gets them unstuck (Priority: P1)

As an operator whose run fails or behaves unexpectedly, I can find my symptom in the guide's
troubleshooting section and recover without help.

**Why this priority**: Most of the pilot's real failures happened during setup, not in the
governed run. Without this, newcomers stop at the first error.

**Independent Test**: Each troubleshooting entry is reproduced deliberately (or from recorded
evidence), and following its instructions resolves it.

**Acceptance Scenarios**:

1. **Given** each failure seen while building the pilot (listed under Edge Cases), **When**
   the operator looks up its visible symptom, **Then** they find the cause and the fix.
2. **Given** a failure the guide doesn't cover, **When** the operator reaches the end of
   troubleshooting, **Then** the guide tells them how to collect redacted diagnostics and
   ask for help, without sharing secrets.

---

### User Story 3 - An evaluator understands the security model before running anything (Priority: P2)

As someone evaluating specfoundry for a team or an enterprise, I can read a short section
that explains what the pilot guarantees and how I'd verify each guarantee myself:
- the gate fails closed;
- workers hold no repository credentials;
- an independent grader;
- human merges;
- no phone-home;
- pinned images.

I also learn which known limits apply today.

**Why this priority**: The project's value is the governed, least-privilege model.
Evaluators need it before they invest time in a run. It explains the run rather than changing
it.

**Independent Test**: A reader can map each stated guarantee to the evidence file or check
that demonstrates it, and to a known limit where one applies.

**Acceptance Scenarios**:

1. **Given** each guarantee, **When** the evaluator reads it, **Then** the guide names the
   check or evidence that proves it in a completed run.
2. **Given** the known limits (e.g. the publisher token belongs to a person until the GitHub
   App work in 004; spend caps may run in token mode), **When** they read the guide, **Then**
   each limit is stated plainly with its planned fix, where one exists.

---

### Edge Cases

These are the real failures from building the pilot. Each needs a troubleshooting entry.

- The model provider returns "no API key passed in": the key must be a file referenced from
  the provider config, and both files must be present.
- The provider reports zero cost: spend runs on the token cap. The guide explains this and
  how to declare prices.
- The publisher-token check says the token can write the project repository: the token is
  scoped too broadly, or the check is misread.
- The publisher-token check fails because the token has expired.
- Every prompt answers "no" immediately: the command was run without an interactive
  terminal.
- Stand-up stops on an image pull error, a wrong CNI hash, or a tag-only image reference.
- The run refuses to start because a pilot PR from an earlier run is still open.
- `resume` says the PR isn't merged yet.
- The worker hits its deadline or spend cap.
- An image-update PR can't be opened because repository settings block automation from
  opening PRs (for people who fork the project).
- Leftover clusters or containers from an interrupted run.

## Requirements *(mandatory)*

### Functional Requirements

**Content**

- **FR-001**: The guide MUST state prerequisites precisely: machine resources, operating
  system support, required accounts, and required tools with versions. Every pinned version
  MUST match the project's pins.
- **FR-002**: The guide MUST walk through provider configuration generically. It MUST work
  for any OpenAI-compatible provider and name no private provider.
- **FR-003**: The guide MUST explain how to create a token scoped to one throwaway
  repository, why the scope matters, and how the pilot checks it.
- **FR-004**: The guide MUST give the full command sequence in order, and explain every
  prompt the operator will see: what it means, what to answer, and what "no" does.
- **FR-005**: The guide MUST explain the merge pause and the resume step, including what to
  review in task A's PR before merging.
- **FR-006**: The guide MUST explain how to read the evidence record: the summary, the audit
  checks, and the refused-egress log.
- **FR-007**: The guide MUST cover teardown and how to confirm nothing is left behind.
- **FR-008**: The guide MUST include a troubleshooting section that covers every edge case
  above, each as symptom → cause → fix.
- **FR-009**: The guide MUST include a security-model section that maps each guarantee to
  the check or evidence proving it, and lists the current known limits with their planned
  fixes.
- **FR-010**: The guide MUST use a real completed run as its worked example, showing the
  actual prompts, outcomes and audit.
- **FR-011**: The guide MUST say which steps will change when planned roadmap entries land:
  the GitHub App publisher (004), OpenShift (005), observability (007) and more harnesses
  (008).
- **FR-012**: The guide MUST say how to collect redacted diagnostics and ask for help, and
  must never ask the operator to share secrets.

**Supported environments**

- **FR-013**: The guide MUST support and be validated on **Linux** (Ubuntu, as tested
  today). It MUST state that macOS is not yet supported, and why: the published images are
  single-architecture (amd64), and Apple Silicon needs multi-architecture images. It MUST
  record that gap as a follow-up for the image workflow.

**Validation**

- **FR-014**: The guide MUST be validated by the **owner on a freshly provisioned
  machine** (or VM) that has never had specfoundry, its tools or its configuration
  installed. The owner follows only the guide, without using this repository's prior
  local state, and notes every hesitation or deviation.
- **FR-015**: Every hesitation, deviation or missing step found during validation MUST be
  fixed in the guide, and the validation run's evidence MUST be committed.
- **FR-016**: Every command and file path in the guide MUST be checked against the
  repository, so none is stale.

**Form**

- **FR-017**: The guide MUST live in the repository as plain documents readable on GitHub,
  linked from the README, with no hosted documentation site (roadmap 006 scope-out).

### Key Entities

- **Operator guide**: the end-to-end document. Its sections are prerequisites, provider
  setup, token setup, the command sequence and prompts, the merge pause, evidence,
  teardown, troubleshooting, and the security model.
- **Troubleshooting entry**: a symptom, its cause, its fix, and how to confirm the fix.
- **Validation run**: a newcomer's run that follows only the guide, with its evidence and a
  list of guide fixes it produced.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The validator (the owner on a fresh machine) completes the pilot to a passing
  audit and verified teardown, using only the guide, with 0 lookups outside it (no source
  code, no prior notes, no help).
- **SC-002**: The newcomer's hands-on time, excluding downloads and the model's work, is
  under 60 minutes.
- **SC-003**: 100% of the edge cases listed in this spec have a troubleshooting entry, and
  each entry's fix is shown to work.
- **SC-004**: 100% of the commands and file paths in the guide resolve against the current
  repository.
- **SC-005**: Every security guarantee in the guide links to the check or evidence that
  proves it (100% coverage).
- **SC-006**: 0 secrets or private provider names appear in the guide or the validation
  evidence.

## Assumptions

- The guide covers the pilot as it stands after 003: plain Jobs; images pulled by digest
  from public GHCR; a fine-grained publisher token. Roadmap 006's mention of "where 003
  (Kelos) will change the steps" is stale: 003 delivered hardened images instead, and Kelos
  is not used.
- The worked example is the most recent verified run: `20261113T180203Z` (003's validation
  on the published images). 002's run `20261113T030655Z` is cited as history.
- The guide is in English, as Markdown in the repository: a new `docs/operator-guide.md`,
  plus links from the README and `pilot/README.md`.
- Provider examples are generic (OpenAI-compatible endpoints); no private provider is
  named.
- Readers are comfortable with a terminal, git and GitHub, but have no prior Kubernetes or
  Spec Kit experience.
- Owner decisions (2026-11-13): Linux only for now, with macOS noted as a gap (it needs
  multi-arch images); validation by the owner on a fresh machine using only the guide.
