# Contract: guide outline and acceptance checks

`docs/operator-guide.md` MUST contain these sections in this order. Each check is verified
during review and by the fresh-machine validation run.

| # | Section | Must include | Check |
|---|---|---|---|
| 1 | What you'll do | the end state (a passing audit and 2 draft PRs on your fixture repo); the time budget; the human steps (2 `y` prompts, 1 merge, 1 approval) | Validator can say up front what success looks like |
| 2 | How specfoundry keeps you safe | each guarantee (fail-closed gate, no SCM credential in workers, independent grader, publisher-only token, human merge, no phone-home, digest-pinned images) → the audit/check that proves it; known limits (token owner = you until 004; token-fallback spend mode; host-side gate; per-run keys → 005) | Every guarantee links to a check ID (P0x/AU0x/GM0x) or evidence file (SC-005) |
| 3 | Before you start | Ubuntu 24.04 LTS amd64; 4+ CPU, 8 GB free RAM, 30 GB disk; GitHub account; a model provider with an OpenAI-compatible endpoint; macOS not yet supported (amd64-only images) | Matches research R2 |
| 4 | Install the tools | Docker Engine (official repo), git, Python 3.12, GitHub CLI + `gh auth login`, `spec` 0.2.0 from its release **with checksum verification**, clone of the public repo; note that `pilot up` installs pinned kind/kubectl | Versions match `pilot/pins.env` (docs check) |
| 5 | Model provider | `~/.config/specfoundry/opencode/` (0700) with `opencode.json` (`{file:…}` reference) + `<provider>_api_key` (0600); `pilot.env` keys incl. `PILOT_MODEL_EGRESS_HOSTS`; optional price declaration for USD caps; link to harnesses.md | No private provider named; generic example only |
| 6 | Fixture repo + scoped token | create an empty public `<name>-pilot-fixture` repo; fine-grained token with only that repo, Contents + Pull requests read/write, short expiry; `pilot/pilot publisher-token` with the expected OK output; why scope matters | `publisher-token` output explained line by line |
| 7 | Stand up | `pilot/pilot up`; what it does; expected output; `reset-fixture` with its warning (force-resets the throwaway repo only) | Expected output quoted |
| 8 | Run the pilot | `pilot/pilot run` in a real terminal; mode prompt; A/1 induced failure explained; retry prompt; A/2 pass; draft PR; pause message: each with real output from run 20261113T180203Z and what "no" does | Every prompt in contracts/cli of 002 covered |
| 9 | Merge pause and resume | what to review in task A's PR; Ready for review → Merge; `pilot/pilot resume`; reconcile proposal and approval; B runs; audit | `resume` before merge (exit 4) and `N` (exit 5) explained |
| 10 | Read the evidence | where it is; `summary.md` walkthrough; audit AU01–AU11 one line each; `proxy-denials.log` (what refusals mean) | Each AU check described |
| 11 | Tear down | `pilot/pilot down` T01–T03; `pilot/pilot audit` (AU07); optional cleanup of fixture PRs/branches and token | Expected output quoted |
| 12 | When something goes wrong | link to troubleshooting by symptom; how to collect redacted diagnostics (`pilot/pilot status`, `run.json`, `events.jsonl`, `job.json`; never config files or keys) and where to open an issue | FR-012 |
| 13 | What will change | 004 (GitHub App identity), 005 (OpenShift, per-run keys), 007 (observability), 008 (more harnesses); macOS needs multi-arch images | Matches roadmap 1.5.0 |

General rules:
- The model provider (5) comes before the fixture repo and token (6), because every
  `pilot/pilot` command, `publisher-token` included, reads `pilot.env` (validation finding,
  2026-11-14).
- Commands appear in fenced `sh` blocks. Quoted outputs appear in `text` blocks labelled
  "from run 20261113T180203Z".
- Placeholders use `<angle-brackets>`. No real tokens, hostnames of private providers, or
  personal data.
