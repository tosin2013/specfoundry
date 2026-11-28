# Tasks: Proven hidden tests (041)

**Input**: `specs/041-proven-hidden-tests/` (spec.md, plan.md, research.md, data-model.md,
contracts/commands.md, quickstart.md)

Stories are built in the plan's order: US1, then US3 (the eval scores with it), then US2, US4,
US5. Each phase is its own pull request. Check every change with `go vet ./... && go test ./...`;
grader changes also with `pilot/images/tests/`.

## Phase 1: User Story 1 - Choose the test author's model separately (Priority: P1) 🎯 MVP

- [x] T001 [US1] `internal/config`: read `FORGE_AUTHOR_MODEL` (target profile first, then the
  global configuration; `PILOT_` alias), with an `AuthorModel()` that falls back to the worker's
  model.
- [x] T002 [US1] `internal/cli/author.go`: pass the author model to the author Job (`JobEnv.Model`)
  for `author start`, `author watch` and step mode; the free-model opt-in applies unchanged.
- [x] T003 [US1] `internal/author`: record `model` in `draft.json`; `PRBody` adds "Drafted by:
  <model>".
- [x] T004 [US1] `doctor`: an `author model` row (PASS when set and different, INFO "drafts use
  the worker's model" otherwise); refuse an author model on another provider than the worker's
  (research R5); probe the key with the author's model when it differs.
- [x] T005 [P] [US1] Tests: config fallback and alias, Job env, draft record, PR body, doctor rows.
- [x] T006 [P] [US1] Docs: `docs/test-author.md` (choosing the author's model), `docs/targets.md`
  (profile key), release notes.

## Phase 2: User Story 3 - Prove drafted tests against a reference change (Priority: P3)

- [ ] T007 [US3] `pilot/images/tools/grade.py`: `mode: reference`: apply the manifest change (029)
  and the reference patch on the base; check the project's tests pass (`REFERENCE_BROKEN`,
  `REFERENCE_DOESNT_APPLY`); per hidden file, run the focused (`FORGE_HIDDEN_TEST_COMMAND`) or
  full test command on the base once and on the reference `repeats` times; per-file verdicts in
  the frame, hidden output only in the separate output file.
- [ ] T008 [P] [US3] `pilot/images/tests/`: reference mode (applies, broken reference, per-file
  pass/fail, flaky, focused command).
- [ ] T009 [US3] `internal/grader`: stage the reference for the grader Job (never the worker);
  `FORGE_REFERENCE_REPEATS` (default 3, min 2), `FORGE_HIDDEN_TEST_COMMAND`.
- [ ] T010 [US3] `internal/author/check.go`: run the reference mode after today's baseline when a
  reference exists; codes `DRAFT_FAILS_ON_REFERENCE`, `DRAFT_PASSES_ON_BASE`, `DRAFT_FLAKY`,
  `REFERENCE_BROKEN`, `REFERENCE_DOESNT_APPLY`; record the result (no output) in `draft.json`.
- [ ] T011 [US3] `internal/author/submit.go`: write `<target>/proofs/NNN[/<slice>].json` (data
  model) into the companion PR; PR body "Reference check: …".
- [ ] T012 [US3] `author prove --target --item [--slice]` (`internal/cli`, `internal/author`):
  prove merged hidden tests and open a companion PR with the proof; classify it in
  `internal/cli/command_audit.go` with `author`.
- [ ] T013 [US3] `internal/readiness`: `HIDDEN_TESTS_UNVERIFIED` (missing, failed or stale proof:
  recompute the hidden tests' tree hash); `reference: none` allows with a warning; doctor's
  reference row.
- [ ] T014 [US3] `internal/checks`: P11r, no reference path or content hash in the attempt's staged
  inputs, ConfigMaps or prompt; add it to the audit.
- [ ] T015 [P] [US3] Go tests: check codes, proof writing and reading, readiness staleness, P11r,
  command audit.
- [ ] T016 [P] [US3] Docs: `docs/test-author.md` (references, proofs, `reference: none`),
  `docs/troubleshooting.md` (the new codes), release notes.
- [ ] T017 [US3] SC-001 on the cluster: owner commits `documcp/references/004.patch` (attempt 2's
  change from run 20261128T012908Z); `author prove --target documcp --item 004` refuses the merged
  test file with `DRAFT_FAILS_ON_REFERENCE`.

## Phase 3: User Story 2 - Score the test author against known cases (Priority: P2)

- [ ] T018 [US2] `internal/author/eval.go`: read `evals/<case>/case.json` from the companion;
  draft each ready case with the current settings, run the reference check (and the vote once
  US4 is built), score; write `~/.local/state/chalkeus/evals/<timestamp>.json`; compare with the
  previous result and report drops.
- [ ] T019 [US2] `author eval [--case]` (`internal/cli`); classify in the command audit with
  `author`; owner-run only.
- [ ] T020 [P] [US2] Tests: case loading, scoring, comparison, `pending` cases.
- [ ] T021 [US2] Owner: add eval cases `documcp-004` (ready) and `documcp-001-us2` (pending until
  it has a reference) to the companion.
- [ ] T022 [P] [US2] Docs: running the eval and reading the score; release notes.

## Phase 4: User Story 4 - Independent votes on each test (Priority: P4)

- [ ] T023 [US4] `internal/author/vote.go`: `FORGE_VOTERS` (default 2, min 2) voter Jobs per hidden
  file with the author Job's isolation; inputs: spec, test plan, the file, the 0–3 scale; JSON
  verdicts; combine (research R6).
- [ ] T024 [US4] Wire the vote after a passing reference check in `author check` / `watch`; a 2–3
  sends the draft back (`DRAFT_VOTED_DOWN`; watch redrafts once with the reasons); disagreement
  opens the PR with every vote shown; votes into the proof and PR body.
- [ ] T025 [P] [US4] Tests: combining votes, send-back, disagreement, PR body.
- [ ] T026 [P] [US4] Docs and release notes.

## Phase 5: User Story 5 - A test plan in the spec (Priority: P5)

- [ ] T027 [US5] `internal/author/criteria.go`: read a `## Test plan` section (one line per
  criterion id); include it in the author's input; the mapping file gets `plan` per test.
- [ ] T028 [US5] `doctor --item`: warn per criterion without a plan line, info when there is no
  plan; the `FORGE_HIDDEN_TEST_COMMAND` hint (plan contracts).
- [ ] T029 [P] [US5] Tests and docs (`docs/test-author.md`: writing a test plan, documcp 004 as
  the example); release notes.

## Phase 6: Polish

- [ ] T030 Debrief against roadmap 041 (`/speckit-roadmap-debrief`); SC-002 is counted from the
  next ten drafts after release.
