# Quickstart: run and validate the M1 pilot

This guide shows how to check, end to end, that the pilot meets [spec.md](spec.md). It
covers commands and expected outcomes only. Design details live in
[research.md](research.md) and [contracts/](contracts/).

## Prerequisites (one time)

- An Ubuntu host with Docker, about 8 GB free RAM, Python 3.12, git, and `gh` logged in
  as the operator. kind and kubectl are installed at pinned versions by `pilot up`.
- `spec` 0.2.0 on PATH, and OpenCode v2.2.7 at `$HOME/.opencode/bin/opencode`.
- An **empty throwaway GitHub repo** whose name ends in `-pilot-fixture`.
- A **fine-grained token** scoped to that repo only, with `contents: write` and
  `pull_requests: write`, placed in `publisher.env`.
- The worker's OpenCode config in `~/.config/specfoundry/opencode/` (`opencode.json` with
  `apiKey: "{file:~/.config/opencode/<provider>_api_key}"`, plus that key file). See
  `docs/harnesses.md` for the harness and provider options.
- `pilot.env` filled in per [contracts/config.md](contracts/config.md). All three files
  `chmod 600`.

## 1. Unit check: the gate fails closed (no cluster needed)

```sh
python3 -m unittest discover -s pilot/tests -v
```

Expected: every case in the fail-closed matrix refuses, and only the fully ready case
allows. The matrix covers exit 2, malformed JSON, wrong schema version,
`complete:false`, a missing item, a duplicate item, an unsatisfied dependency, an
error diagnostic, an inconsistent `blocked_count`, and an already-verified item.
(SC-005)

## 2. Stand up and reset

```sh
pilot/pilot up
pilot/pilot reset-fixture        # confirm with y
pilot/pilot gate B               # expect exit 10, reason DEP_UNSATISFIED:001
pilot/pilot gate A               # expect exit 0, decision allow
```

## 3. Run the first half

```sh
pilot/pilot run
```

Expected, in order (see `evidence/<run>/events.jsonl`):

0. The mode prompt shows `step-by-step` with its caps. Answer `y`.
1. Gate A → allow. Gate B → refuse.
2. A/1 runs with induction `withheld-acceptance-section`. Its grade is **fail**
   (G5_hidden_tests). No PR. Gate B → refuse. Answer `y` at
   `Retry A (attempt 2 of 3)?`.
3. A/2 runs without induction. Its grade is **pass**. The publisher opens **one draft
   PR** for A.
4. Gate B → refuse (A's PR is not merged yet). The run pauses: `awaiting-merge`, exit 0.

Check: `gh pr list -R $PILOT_FIXTURE_REPO --state open` shows exactly 1 draft PR, and
its author is the publisher token's identity.

## 4. Human merge, then resume

1. Review and **merge A's draft PR on GitHub yourself**.
2. Run:

```sh
pilot/pilot resume
```

Expected: reconcile shows the proposed edit `001: planned → verified` and asks `y/N`.
Answer `y`. Then: gate B → allow, B/1 → pass, one draft PR for B, the audit passes,
exit 0.

Negative checks (optional):
- `pilot resume` **before** merging → exit 4, gate B still refuses.
- Answer `N` at reconcile → exit 5, the roadmap is unchanged, B never starts.
- Answer `N` at the retry prompt → exit 6, no attempt starts; `pilot resume` re-asks.
- Start `pilot run` while an earlier run's `pilot/*` PR is open → exit 2.

## 5. Audit from evidence only, then tear down

```sh
pilot/pilot audit                # AU01–AU11 all pass (SC-001…SC-004, SC-007, SC-008)
pilot/pilot down                 # T-checks pass: cluster, registry, proxies gone (SC-006)
git add specs/002-m1-gated-pilot/evidence/<run-id> && git commit
```

## Pass criteria

- `audit.jsonl`, `checks/results.jsonl` and `teardown.jsonl` show 0 failures.
- `prs.json` holds exactly 2 draft PRs, both by the publisher. The system merged neither.
- The redaction scan is clean.
