# Research: Operator guide

**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-11-13

## R1 — One guide document plus a troubleshooting document

- **Decision:** `docs/operator-guide.md` is the end-to-end path, read top to bottom.
  `docs/troubleshooting.md` holds the symptom-indexed entries (FR-008), and the guide links
  into it at each step where a failure is likely. The security model (US3) is a section of
  the guide, placed early, so evaluators read it before installing anything.
- **Rationale:** A newcomer follows one linear document, while troubleshooting is searched
  by symptom. Two files keep both usable, and GitHub renders each with a table of contents.
- **Alternatives considered:** One huge file (hard to search by symptom). A docs site
  (out of scope for roadmap 006).

## R2 — Validated baseline: Ubuntu 24.04 LTS, amd64

- **Decision:** The guide's supported and validated platform is Ubuntu 24.04 LTS on amd64:
  - 4+ CPUs, 8 GB RAM free, 30 GB disk;
  - Docker Engine from Docker's apt repository;
  - Python 3.12 (the system Python on 24.04);
  - git;
  - GitHub CLI.

  `kind` and `kubectl` are installed at pinned versions by `pilot up` itself. `spec` 0.2.0
  is installed from its GitHub release, verified with `spec_0.2.0_checksums.txt`. macOS is
  noted as unsupported, because the images are amd64-only (owner decision; spec FR-013).
- **Rationale:** This is what 001–003 were verified on. Python 3.12 matches the
  orchestrator's requirement with no extra install.
- **Verify at implement:** each install command, on the fresh validation machine.

## R3 — Provider setup stays generic

- **Decision:** The guide uses an OpenAI-compatible example (a placeholder `baseURL` and
  model). It shows the two-file layout (an `opencode.json` with a
  `{file:~/.config/opencode/<provider>_api_key}` reference, plus the key file), and links
  to `docs/harnesses.md` for detail. No private provider is named; the guide says any
  OpenAI-compatible gateway works.
- **Rationale:** This is the configuration that worked in practice (002 R1 findings), and it
  follows the project's rule never to name private providers.

## R4 — Every prompt and pause explained from the real run

- **Decision:** The guide quotes the real prompts and outputs of run `20261113T180203Z`
  (`specs/003-m2-kelos-backend/evidence/20261113T180203Z/`):
  - the mode prompt;
  - the retry prompt;
  - the merge pause message;
  - the reconcile proposal;
  - the audit lines;
  - the summary table.

  The real output is shown in collapsible blocks next to each explanation.
- **Rationale:** Spec FR-004, FR-010. Real output lets the operator tell "expected" from
  "wrong" at a glance.

## R5 — Troubleshooting entries come from recorded failures

- **Decision:** Each of the 11 edge cases in the spec becomes one entry with **Symptom**
  (the exact message), **Cause**, **Fix** and **Confirm**. Each entry cites its source: the
  002/003 research notes, the evidence files, or the commit that fixed it. Entries for
  failures that can be safely reproduced are re-checked during validation (SC-003):
  - a tag-only image reference;
  - a wrong CNI hash;
  - running without a terminal;
  - an open earlier pilot PR;
  - `resume` before merge.

  Failures that can't be safely reproduced (for example, a provider returning a 401) are
  checked against recorded evidence.
- **Rationale:** Real symptoms, not guesses.

## R6 — Keeping the guide correct: a docs check

- **Decision:** Add `pilot/tools/docs_check.py` (Python 3.12, stdlib only) and a
  `docs-check` GitHub workflow that runs on PRs touching `docs/**`, `README.md` or
  `pilot/**`. The check:
  - extracts every `pilot/pilot <subcommand> [--flags]` from the guide's fenced code blocks
    and confirms the subcommand and flags exist in `pilot/pilot --help`/`<sub> --help`;
  - confirms every repository-relative path referenced in links or backticks exists;
  - confirms the pinned versions quoted in the guide (kind, kubectl, Calico, spec,
    OpenCode) match `pilot/pins.env`;
  - runs the evidence redaction patterns (from `pilot/specfoundry_pilot/audit.py`) over the
    docs, to catch token-like strings.

  Private provider names can't be checked in CI, because listing them would publish them.
  The validator checks that locally, against their own provider host, with
  `grep -F -f` (SC-006).
- **Rationale:** FR-016 and SC-004 need staleness caught continuously, not just once.
  Reusing `audit.redaction_scan` keeps one definition of "looks like a secret".
- **Alternatives considered:** A manual review only (stale within weeks). A full doc-test
  harness that runs every command (needs a cluster in CI; too heavy for M-level docs).

## R7 — The validation run on a fresh machine

- **Decision:** The owner provisions a fresh Ubuntu 24.04 machine or VM that has never had
  specfoundry, kind, the `~/.config/specfoundry/` files or a cloned repo. They clone the
  public repo and follow only `docs/operator-guide.md`, keeping a log of:
  - timestamps per section;
  - each hesitation, deviation or outside lookup;
  - commands typed.

  The run's evidence is committed to `specs/006-operator-guide/evidence/<run-id>/`. The
  validation log is committed as `specs/006-operator-guide/evidence/validation-log.md`
  (redacted). Every finding becomes a guide fix before 006 is verified (FR-015).
- **Rationale:** This is your decision (FR-014). The log makes SC-001 and SC-002
  measurable.
- **Notes:**
  - The validator still answers the pilot's human prompts and merges task A's PR (by design).
  - A throwaway fixture repo and a scoped token are needed again. The existing
    `craz3-pilot-fixture` can be reused after `reset-fixture`, with a new token if the
    old one has expired.

## R8 — README and pilot/README point at the guide

- **Decision:** The README's "Try the pilot" section becomes a 5-line summary linking to the
  guide. `pilot/README.md` links to it as the user documentation and keeps the developer
  reference.
- **Rationale:** One source of truth for operators; no drift between three copies of the
  steps.
