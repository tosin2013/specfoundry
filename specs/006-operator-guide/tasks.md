---
description: "Task list for 006 — Operator guide: repeat the pilot from zero"
---

# Tasks: Operator guide — repeat the pilot from zero

**Input**: Design documents from `specs/006-operator-guide/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) (R1–R8),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included for the docs check. The plan's Testing section requires unit tests
covering an unknown subcommand/flag, a missing path, a version mismatch and token-like
strings. The guide itself is validated by the owner's fresh-machine run.

**Organization**:
- US1 = the newcomer path (P1, MVP)
- US2 = troubleshooting (P1)
- US3 = the security model for evaluators (P2)

**Conventions**:
- Docs are GitHub-rendered Markdown.
- Commands go in fenced `sh` blocks. Quoted outputs go in `text` blocks labelled "from run
  20261113T180203Z", taken verbatim from
  `specs/003-m2-kelos-backend/evidence/20261113T180203Z/`.
- Placeholders use `<angle-brackets>`.
- **No secrets, private provider names, hostnames or personal data anywhere.**

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Create `docs/operator-guide.md` with the 13 section headings from contracts/guide-outline.md in order (placeholder sentences only), and `docs/troubleshooting.md` with an intro and an empty "Index by symptom" table
- [X] T002 [P] Create `specs/006-operator-guide/evidence/validation-log.md` from the data-model template:
  - a machine description (OS, CPU, RAM; no hostnames or IPs);
  - a table `| Section | Start | Duration | Hesitations / deviations / outside lookups | Guide fix (commit) |`;
  - a total hands-on time;
  - the result of the local provider-name scan.

---

## Phase 2: Foundational — docs check (blocks every story's verification)

- [X] T003 Write `pilot/tests/test_docs_check.py` (write first; it fails until T004). Using temp Markdown files, assert:
  - **D1:** `pilot/pilot run` in an `sh` block passes; `pilot/pilot run --bogus` and `pilot/pilot frobnicate` fail with `<file>:<line>` in the message;
  - **D2:** an existing path (`pilot/pins.env`) passes; `pilot/images/lock` fails; URLs, `~/...` paths and `<placeholders>` are ignored;
  - **D3:** "kind v0.27.0" passes and "kind v0.26.0" fails, using the values in `pilot/pins.env`;
  - **D4:** a string built at runtime as `"gh" + "p_" + 30 chars` fails, and ordinary text passes;
  - **exit codes:** 0 when clean, 1 with every failure listed.
- [X] T004 Implement `pilot/tools/docs_check.py` per contracts/docs-check.md (Python 3.12, stdlib):
  - get the subcommands and flags by running `pilot/pilot --help` and `pilot/pilot <sub> --help` via subprocess (parse the argparse output);
  - paths: Markdown links `](path)` and inline `` `path` `` tokens containing `/`, with no spaces, `<`, `://` or a leading `~`, resolved from the repo root and from the file's directory for links;
  - versions: regexes for `kind v…`, `kubectl v…`, `Calico v…`, `spec 0.…`, `OpenCode v…`/`2.2.7`, compared with `pilot/pins.env`;
  - secrets: `specfoundry_pilot.audit.PATTERNS`;
  - default files: `docs/*.md README.md pilot/README.md`.
- [X] T005 [P] Create `.github/workflows/docs-check.yml`:
  - trigger: `pull_request` on `docs/**`, `README.md`, `pilot/**` and the workflow file;
  - one job on `ubuntu-24.04` with `permissions: contents: read`;
  - checkout pinned by SHA (`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`);
  - run `python3 pilot/tools/docs_check.py` and `PYTHONPATH=pilot python3 -m unittest pilot.tests.test_docs_check`;
  - no secrets.
- [X] T006 Run `python3 pilot/tools/docs_check.py` on the current `README.md`, `pilot/README.md` and `docs/harnesses.md`, and fix any existing failures in those files

**Checkpoint**: the docs check passes on the existing docs; its unit tests pass.

---

## Phase 3: User Story 1 — A newcomer completes the pilot using only the guide (Priority: P1) 🎯 MVP

**Goal**: Sections 1 and 3–11 of the guide, plus 13 (outline rows 1, 3–11, 13).

**Independent Test**: quickstart.md §3. The owner, on a fresh Ubuntu 24.04 machine, follows only the guide to audit 11/11 and teardown 3/3, logging 0 outside lookups (SC-001), with hands-on time ≤ 60 min (SC-002).

- [X] T007 [US1] Write section 1 "What you'll do" in `docs/operator-guide.md`:
  - the end state: a passing audit, 2 draft PRs on your fixture repo (you merge one), and teardown verified;
  - the time budget (about 60 min hands-on plus downloads and model time);
  - the human steps: 2 `y` prompts, 1 PR merge, 1 approval;
  - a 6-step overview diagram (text).
- [X] T008 [US1] Write section 3 "Before you start" in `docs/operator-guide.md`:
  - Ubuntu 24.04 LTS amd64, 4+ CPU, 8 GB free RAM, 30 GB disk;
  - a GitHub account;
  - a model provider with an OpenAI-compatible endpoint and an API key;
  - a short "macOS: not yet supported (images are amd64-only; Apple Silicon needs multi-arch images — planned)" note.
- [X] T009 [US1] Write section 4 "Install the tools" in `docs/operator-guide.md`:
  - **Docker Engine:** commands from Docker's official Ubuntu instructions (link to them), then add the user to the `docker` group and log out and back in;
  - **apt packages:** `git`, `python3` (3.12 on 24.04), `curl`;
  - **GitHub CLI:** from its official apt repo (link), then `gh auth login`;
  - **spec 0.2.0:** download `spec_0.2.0_linux_amd64.tar.gz` and `spec_0.2.0_checksums.txt` from `https://github.com/tosin2013/spec-status/releases/tag/v0.2.0`, run `sha256sum -c --ignore-missing spec_0.2.0_checksums.txt`, extract, and install to `~/.local/bin`;
  - `git clone https://github.com/tosin2013/specfoundry && cd specfoundry`;
  - a note that `pilot up` installs pinned kind v0.27.0 and kubectl v1.32.2 itself;
  - finish with a one-line check: `docker run --rm hello-world && gh auth status && spec --version && python3 --version`.
- [X] T010 [US1] Write section 5 "Prepare a throwaway fixture repo and a scoped token" in `docs/operator-guide.md`:
  - create an empty **public** repo named `<anything>-pilot-fixture` (no README); explain that it gets force-reset;
  - a fine-grained token: Repository access → *Only select repositories* → the fixture; Permissions → Contents and Pull requests: read and write; a short expiry;
  - `pilot/pilot publisher-token`, with the expected `publisher token: OK` output from contracts and every line explained (including `canary_push: False` meaning it can't write this project's repo);
  - why scope matters: workers never hold it, and only the publisher Job does;
  - the note that the PRs will show your account as author until 004.
- [X] T011 [US1] Write section 6 "Configure your model provider" in `docs/operator-guide.md`:
  - `install -d -m 700 ~/.config/specfoundry/opencode`;
  - the key in `<provider>_api_key` (mode 600);
  - a generic `opencode.json` example with `"apiKey": "{file:~/.config/opencode/<provider>_api_key}"` and a placeholder `baseURL`/model;
  - `~/.config/specfoundry/pilot.env` with `PILOT_FIXTURE_REPO`, `PILOT_MODEL`, `PILOT_MODEL_EGRESS_HOSTS`, `PILOT_SPEND_CAP_USD`, `PILOT_TOKEN_CAP` (mode 600);
  - an optional per-token price declaration for USD caps;
  - a check on the host: `opencode run --standalone … "Reply with ok"`, if OpenCode is installed locally (optional);
  - a link to `docs/harnesses.md`;
  - name no private provider.
- [X] T012 [US1] Write section 7 "Stand up" in `docs/operator-guide.md`:
  - `pilot/pilot up`: what it does (pinned kind and kubectl, kind + Calico with the hash checked, images pulled by digest from `pilot/images.lock`, egress proxies, the publisher namespace); the typical duration; the expected final line `== up complete`;
  - `pilot/pilot reset-fixture`: a warning that it force-resets **only** the fixture repo, the confirmation prompt, and the expected `fixture reset: … = <sha>`;
  - optionally `pilot/pilot gate A` and `pilot/pilot gate B`, with the expected allow/refuse.
- [X] T013 [US1] Write section 8 "Run the pilot, every prompt explained" in `docs/operator-guide.md`. Use the real output from `specs/003-m2-kelos-backend/evidence/20261113T180203Z/` (`events.jsonl`, `summary.md`) and the session output:
  - **Terminal:** run it in a real terminal, because a missing TTY counts as "no".
  - **GM01–GM04:** the gate self-checks.
  - **Mode prompt:** what each field means, `y`, and that "no" exits 5 and stages nothing.
  - **A/1:** induced on purpose (the acceptance section is withheld), so it fails on G5.
  - **Live checks P01–P08**, in one line each.
  - **Retry prompt:** `y`; "no" pauses with exit 6, and `resume` asks again.
  - **A/2:** passes; P09/P10; the draft PR is opened by the publisher; gate B still refuses.
  - **The pause message.**
- [X] T014 [US1] Write section 9 "The merge pause, then resume" in `docs/operator-guide.md`:
  - what to review in task A's PR (the 4 changed files; `slug.py` follows the spec);
  - *Ready for review* → *Merge*; any merge method works;
  - `pilot/pilot resume`, and the real reconcile proposal text;
  - `y` to approve `001 → verified`; then B's attempt, B's draft PR and the audit lines;
  - `resume` before the merge gives exit 4; "no" at reconcile gives exit 5 and leaves the roadmap unchanged.
- [X] T015 [US1] Write section 10 "Read the evidence and the audit" in `docs/operator-guide.md`:
  - the evidence path (`specs/<active feature>/evidence/<run-id>/`, the active feature from `.specify/feature.json`; `PILOT_EVIDENCE_FEATURE` overrides);
  - `summary.md` walked through with the real table;
  - AU01–AU11, one plain sentence each;
  - `proxy-denials.log`: refusals are expected and show the allowlist working (real example: `bootstrap.pypa.io`, `github.com`);
  - `config.json` stores only a hash of the model host.
- [X] T016 [US1] Write section 11 "Tear down and confirm" in `docs/operator-guide.md`:
  - `pilot/pilot down`, with the T01–T03 expected output;
  - `pilot/pilot audit`, with AU07 now included;
  - optional cleanup: close the fixture PRs, delete the token, delete the fixture repo.
- [X] T017 [US1] Write section 13 "What will change" in `docs/operator-guide.md`:
  - **004:** a GitHub App publisher identity, so PRs show a bot;
  - **005:** OpenShift, possibly Quay images, per-run keys;
  - **007:** operator observability;
  - **008:** Claude Code and Codex harnesses;
  - **macOS:** multi-arch images;
  - each with a link to its roadmap entry.
- [X] T018 [US1] Link the guide from `README.md` (replace the "Try the pilot" command block with a 3–5 line summary plus a link to `docs/operator-guide.md`) and from `pilot/README.md` (a "User documentation" line at the top); keep `pilot/README.md` as the developer reference
- [X] T019 [US1] Run `python3 pilot/tools/docs_check.py` and fix every failure in `docs/operator-guide.md`, `README.md` and `pilot/README.md`

**Checkpoint**: the guide reads end to end; the docs check passes. Ready for the owner's fresh-machine run (T028).

---

## Phase 4: User Story 2 — Troubleshooting gets them unstuck (Priority: P1)

**Goal**: `docs/troubleshooting.md` with every required entry (data-model.md list), each with **Symptom / Cause / Fix / Confirm / Source**, plus links from the guide.

**Independent Test**: quickstart.md §4. Five failures, triggered on purpose, are each fixed using only the troubleshooting doc, and all 13 entries are present (SC-003).

- [X] T020 [P] [US2] Write the setup and configuration entries in `docs/troubleshooting.md`:
  - `no-api-key`: symptom `Authentication Error, No api key passed in.`; cause: the key isn't a `{file:}` reference or the key file is missing; source: 002 research R1/R2 notes;
  - `cost-zero`: symptom: `cap_mode: token-fallback` with `cost_usd: 0`; fix: declare prices; source: 002 research R2;
  - `token-writes-project`: symptom `token can write <owner>/specfoundry`; source: commit `7570552`;
  - `token-expired`: symptom: `token rejected by GitHub (HTTP 401)` / `expires:` in the past.
- [X] T021 [P] [US2] Write the stand-up entries in `docs/troubleshooting.md`:
  - `image-pull-error`: symptom: `image pull failed: … (ImagePullBackOff)`;
  - `cni-hash-mismatch`: symptom: `Calico manifest hash mismatch: expected …, got …`;
  - `tag-only-image`: symptom: `not a digest reference`;
  - `leftovers`: fix `pilot/pilot down`, and confirm T01–T03;
  - each citing the 003 evidence (`specs/003-m2-kelos-backend/spec.md` Evidence).
- [X] T022 [P] [US2] Write the run-time entries in `docs/troubleshooting.md`:
  - `prompts-answer-no`: symptom: `MODE_NOT_CONFIRMED` within a second, with no prompt shown; cause: no TTY; source: 002 run `20261113T030451Z`;
  - `open-pilot-pr`: symptom: `open pilot PRs exist … run pilot reset-fixture first`;
  - `resume-not-merged`: exit 4 message;
  - `deadline-or-spend-cap`: `attempt_failed deadline|spend_cap`; what to check in `report.json`.
- [X] T023 [P] [US2] Write the contributor entry `actions-cannot-open-prs` in `docs/troubleshooting.md`: symptom `GitHub Actions is not permitted to create or approve pull requests`; fix: Settings → Actions → General → Workflow permissions; source: `specs/003-m2-kelos-backend/evidence/ci.md`
- [X] T024 [US2] Fill the "Index by symptom" table at the top of `docs/troubleshooting.md` (symptom text → anchor). Write guide section 12 "When something goes wrong" in `docs/operator-guide.md`:
  - links into troubleshooting;
  - how to collect redacted diagnostics: `pilot/pilot status`, `events.jsonl`, `job.json`, `report.json`, never `~/.config/specfoundry/*` or keys;
  - where to open an issue, and private security reporting.

  Add per-step "If this fails, see …" links in sections 4–11.

**Checkpoint**: 13 of 13 entries present; the docs check passes.

---

## Phase 5: User Story 3 — An evaluator understands the security model (Priority: P2)

**Goal**: Guide section 2. Every guarantee maps to its proof, and the known limits are stated.

**Independent Test**: every guarantee in section 2 links to a check ID (P0x, AU0x, GM0x) or an evidence file (SC-005), and every known limit names its planned fix.

- [X] T025 [US3] Write section 2 "How specfoundry keeps you safe" in `docs/operator-guide.md`, as a table of guarantee → how → proof:
  - fail-closed gate → GM01–GM04, AU01, AU05;
  - no SCM credential in workers → P04, P09, AU04;
  - egress only to the model host → P06, `proxy-denials.log`;
  - independent grader with no network → P07, P08, G1–G5;
  - publisher-only token, draft PRs → AU03;
  - human mode, retry and merge → AU09, AU10, and the reconcile approval;
  - induction proof → AU11;
  - spend cap → AU06;
  - no phone-home → C-10 and the refused-egress evidence;
  - digest-pinned public images with provenance and SBOM → P10, `pilot/images.lock`, `specs/003-m2-kelos-backend/evidence/ci.md`;
  - a mutation test showing the checks aren't vacuous → `specs/002-m1-gated-pilot/evidence/20261113T030655Z/mutation.md`.
- [X] T026 [US3] Add "Known limits today" to section 2 in `docs/operator-guide.md`:
  - PR author = the token owner until 004 (GitHub App);
  - spend caps run in token mode when the provider reports no cost;
  - the gate runs on the host (no spec-status image yet);
  - long-lived provider key copied per attempt (revisit in 005);
  - single-node kind only;
  - Linux only.

  Link the 003 Kelos comparison as further reading.

**Checkpoint**: SC-005 satisfied by review.

---

## Phase 6: Polish & Validation

- [X] T027 Run `python3 pilot/tools/docs_check.py` and `PYTHONPATH=pilot python3 -m unittest discover -s pilot/tests -t pilot`, and fix any failures. Then do a self-review of `docs/operator-guide.md` and `docs/troubleshooting.md` against contracts/guide-outline.md row by row, and against the spec's 11 edge-case bullets (all covered by the 13 entries).
- [ ] T028 **Owner action — fresh-machine validation** (quickstart.md §3, FR-014):
  - on a fresh Ubuntu 24.04 machine, follow only the guide (from GitHub) to audit 11/11 and teardown 3/3;
  - fill `specs/006-operator-guide/evidence/validation-log.md`;
  - copy the run's evidence to `specs/006-operator-guide/evidence/<run-id>/`.
- [ ] T029 Fix every hesitation, deviation and lookup recorded in `specs/006-operator-guide/evidence/validation-log.md`, one commit per finding (link each commit in the log); re-run the docs check
- [ ] T030 **Owner action — troubleshooting spot checks** (quickstart.md §4), on the validation machine: a tag-only image, a wrong CNI hash, no TTY, an open pilot PR, `resume` before merge, each resolved with `docs/troubleshooting.md` only. Record the results in `specs/006-operator-guide/evidence/validation-log.md`.
- [X] T031 Local privacy check (SC-006): `grep -rniF '<model host>' docs/ specs/006-operator-guide/` returns nothing, and `pilot/pilot audit --run <run-id>` gives AU08 pass. Record the result in `specs/006-operator-guide/evidence/validation-log.md`.
- [ ] T032 Add an Evidence section to `specs/006-operator-guide/spec.md` (validation run, log, hands-on time). Then run `/speckit-roadmap-debrief`, and with your approval `/speckit-roadmap-write`: 006 status, Spec dir, and the stale "003 (Kelos)" wording in 006's scope fixed.

---

## Dependencies & Execution Order

- **Phase 1 → Phase 2** (the docs check) → US1, US2, US3. The stories can be written in parallel because they touch different sections or files, but sections in the same file are edited one at a time.
- **US1** T007–T017 edit `docs/operator-guide.md` in order; T018 edits the READMEs; T019 runs after the US1 writing.
- **US2** T020–T023 edit `docs/troubleshooting.md` (they're [P] because each covers a separate block of entries; merge them carefully); T024 touches both files, after US1.
- **US3** T025–T026 edit section 2 of the guide; they can run any time after T001.
- **Validation:** T027 → T028 (owner) → T029 → T030 (owner) → T031 → T032.

### Parallel Opportunities

- T002 alongside T001.
- T005 alongside T003 and T004.
- T020, T021, T022 and T023: four independent troubleshooting blocks.
- US3 (T025–T026) alongside US2.

---

## Implementation Strategy

### MVP

Phases 1–3 (the docs check plus the main path of the guide). That's enough for you to start
the fresh-machine run. Troubleshooting (US2) can be written alongside, and is needed by T030.

### Owner actions (not automatable)

- Provision the fresh Ubuntu 24.04 machine.
- Create a new scoped token if the current one has expired.
- Follow the guide; answer the two prompts; merge task A's PR; approve the reconcile.
- Do the five troubleshooting spot checks.
- Approve the roadmap update.

---

## Notes

- Never paste real tokens, provider hostnames or personal data into the docs or the
  evidence.
- Quoted outputs are verbatim from evidence; don't hand-edit them except to redact.

## Implementation notes (2026-11-13)

- **Analysis H1:** D2 treats only Markdown links and inline-code tokens that start with a
  top-level repo entry (`pilot/`, `specs/`, `docs/`, `test/`, `.github/`, `.specify/`, or a
  top-level file) as repo paths. Domains, owner/repo slugs, `~` paths, `<placeholders>` and
  URLs are never checked (covered by `test_not_paths_h1`). Fixture-repo paths in the guide sit
  in `text` blocks, so they aren't mistaken for repo paths.
- **Analysis H2:** `paths.evidence_root()`:
  - a fresh clone writes evidence to `pilot/runs/<run-id>/`, which is git-ignored;
  - maintainers get the active spec's `evidence/` folder (`.specify/feature.json`, or
    `PILOT_EVIDENCE_FEATURE`).

  Tested in `pilot/tests/test_pins.py`; documented in guide section 10.
- **Analysis M1:** the verbatim console transcript of run `20261113T180203Z` is saved as
  `specs/003-m2-kelos-backend/evidence/20261113T180203Z/console.txt`, and guide sections 8–9
  quote it.
- **T027:**
  - the docs check finds 0 problems in 6 files, and all 109 unit tests pass;
  - the negative check (`pilot/pilot run --bogus`) exits 1 and names the line;
  - all 13 outline sections are in order;
  - all 13 troubleshooting entries are present, with stable anchors;
  - a local scan for the model host finds nothing in `docs/`, the READMEs or this spec.

## Validation findings (2026-11-14, round 1)

- **F1: `publisher-token` came before `pilot.env` existed.** Guide sections 5 and 6 are
  swapped (b4868d6), and missing-config errors now name the fix.
- **F2 (owner feedback): reuse an existing OpenCode setup.** New command
  `pilot/pilot import-opencode`:
  - copies only the default model's provider and its key file, using `install -m 600`;
  - writes `pilot.env`, or compares it with an existing one, without ever printing the host;
  - refuses literal keys and `{env:}` references, and won't overwrite without `--force`.

  New `docs/providers.md` takes over provider setup and spend caps from `harnesses.md`.
  OpenCode stays the default harness for the release.
- **F3: a token that failed the scope check was still saved.** The first token on the
  validation machine could also write this repo (`canary_push: True`); the check reported
  NOT OK, but `publisher.env` already held the token. `publisher-token` now writes to a
  staging file and only replaces `publisher.env` when the check passes; a failing token is
  deleted and any previous token is kept. Guide section 6 and the troubleshooting entry say so.

**Round 1 result:** run `20261114T160532Z` on the validation machine: audit 11/11 (AU07
after `down`), both fixture PRs merged by the owner. Still open: machine details, timings
and teardown rows in `evidence/validation-log.md` (T028), copying the run's evidence into
`evidence/20261114T160532Z/` (T028), and the troubleshooting spot checks (T030).
