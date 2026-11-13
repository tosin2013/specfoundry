# Contract: `pilot` CLI

Entry point: `pilot/pilot` (a bash shim that runs `python3 -m specfoundry_pilot`). All
commands run from the specfoundry repo root. Configuration is in [config.md](config.md).

| Command | Does | Exit codes |
|---|---|---|
| `pilot up` | Install pinned tools, then create the kind cluster + Calico, the local registry, the images (built, pushed and resolved to digests), the egress proxies, the publisher namespace and its Secret | 0 ok · 2 setup failed |
| `pilot publisher-token [--check-only]` | Prompt (hidden input) for the fine-grained token and write `publisher.env` (0600) directly from the shell, then verify: the token can write the fixture repo and list its PRs, cannot write this repo's `origin`, and its expiry is read. Also run automatically by `pilot up` | 0 ok · 1 check failed · 2 no token written |
| `pilot reset-fixture` | Force-reset the throwaway repo's default branch to `pilot/fixture/`, and close open `pilot/*` PRs. Interactive confirmation unless `--yes` | 0 ok · 3 refused (repo guard) · 2 error |
| `pilot run` | Start a new run: gate A, then attempt(s), grade, publish A, then gate B (must refuse), then pause at `awaiting-merge` | 0 paused ok · 1 run failed · 2 error (incl. open `pilot/*` PRs exist) · 5 mode not confirmed · 6 awaiting retry |
| `pilot resume [--run <id>]` | Reconcile A (propose, then ask `y/N`), apply, gate B, then attempt(s), grade, publish B, then audit. Also resumes `awaiting-publish` (re-runs the publisher for the recorded passing attempt; idempotent per R8) and `awaiting-retry` (re-asks the retry prompt) | 0 succeeded · 1 run failed · 4 still awaiting merge · 5 operator declined · 6 awaiting retry |
| (prompt inside `run`/`resume`) | After a failed grade: `Retry <task> (attempt n of 3)? [y/N]`. `N`, EOF or no TTY → run paused `awaiting-retry` | 6 paused awaiting retry |
| `pilot gate <A/B> [--root <dir>]` | Evaluate the gate only, print the decision JSON, and create nothing | 0 allow · 10 refuse |
| `pilot audit [--run <id>]` | Re-run the evidence-only audit (Story 3) on a committed record | 0 pass · 1 fail |
| `pilot down` | Tear down the cluster, registry and proxies, then verify removal (T-checks) | 0 verified · 1 leftovers |
| `pilot status [--run <id>]` | Print the run state from `run.json` | 0 |

Rules:
- No command merges a PR. No code path calls a merge API.
- `run` and `resume` refuse to start when `pilot up` has not completed (exit 2).
- `gate` exits 10 for **every** refusal, including unevaluable input (fail closed).
- All commands append to the run's `events.jsonl` when a run is active.
- `run` shows the mode (`step-by-step` and its caps) and requires a typed `y` before any worker is staged. No TTY → exit 5.
- Every attempt after the first needs a `y` at the retry prompt. No TTY counts as `N` (fail closed).
- `pilot resume` on a run in `awaiting-retry` asks the retry prompt again.
- `run` refuses (exit 2) while any open PR with a `pilot/` head exists on the throwaway repo.
- `RETRY_LIMIT` (default 2) can be lowered but not raised above 2 in M1.
