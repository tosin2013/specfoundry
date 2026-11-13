# Contract: operator configuration

Operator configuration lives **outside the repo**, under
`${SPECFOUNDRY_CONFIG:-~/.config/specfoundry}/`: `pilot.env` and `publisher.env` (each mode
`0600`) and the directory `opencode/` (mode `0700`; files `0600`). `pilot up` and `pilot run`
refuse looser modes. Secret material is only ever passed **by path** to `kubectl create
secret` and never read into the orchestrator's memory or logs (R12).

## `pilot.env` (not secret)

```sh
PILOT_FIXTURE_REPO=owner/specfoundry-pilot-fixture   # throwaway repo; name must end in "-pilot-fixture" (repo guard)
PILOT_FIXTURE_BRANCH=main
PILOT_MODEL=<provider>/<model>                       # passed to `opencode run --model`
PILOT_MODEL_EGRESS_HOSTS=api.example-provider.com    # comma list; the model proxy allowlist
PILOT_SPEND_CAP_USD=1.00
PILOT_TOKEN_CAP=2000000
PILOT_PROVIDER_CAP_DECLARED=false                    # true if a provider-side per-key cap is set
```

## `opencode/` (secret → worker namespace Secret `model-key`, one per attempt)

The worker's OpenCode config directory, verified against OpenCode 2.2.7 on 2026-11-13. Its
files are mounted read-only at `/home/worker/.config/opencode` in the worker pod:

```text
opencode/
├── opencode.json        # provider + model config; apiKey MUST be a reference, e.g.
│                        #   "apiKey": "{file:~/.config/opencode/<provider>_api_key}"
└── <provider>_api_key   # the key itself (one file per provider)
```

- Only `opencode.json` and `*_api_key` files are used. Backups such as `*.bak.*` are ignored.
- `pilot run` rejects an `opencode.json` that holds a literal secret in any
  key/token/secret/password field, and any file whose name looks like an SCM credential
  (`GITHUB|^GH_|GIT_.*TOKEN`).
- Passing the key through environment variables (`{env:...}`, `OPENCODE_CONFIG_CONTENT`)
  did not authenticate in testing; use the file reference.
- To report USD spend (and enforce the $1 cap as `cost` rather than `token-fallback`), add
  per-million-token prices to the model entry; see `docs/harnesses.md`.

## `publisher.env` (secret → `pilot-publish` Secret `scm-token`, created by `pilot up`)

```sh
PILOT_SCM_TOKEN=github_pat_...   # fine-grained, only the throwaway repo; contents:write, pull_requests:write
```

Create it with `pilot/pilot publisher-token`. That command reads the token through a hidden
prompt straight into this file, then verifies its scope in a child process (fixture repo
writable, PRs listable, `origin` **not** writable, expiry reported). `pilot up` repeats the
check and stops if it fails. GitHub has no API for creating fine-grained tokens, so
generating the token stays a manual step; a GitHub App with per-run installation tokens is
the automated successor (proposed for roadmap 004).

Host-side reads (`gh` merge status, PR listing) and the operator-approved status push
(R9) use the operator's own existing `gh`/git login, never `publisher.env`.

A fine-grained token is owned by a GitHub user. If it is the operator's own account, PRs show
the operator as author; the evidence then records `publisher_identity` (the token's login)
and AU03 checks PR author == publisher identity. Use a separate bot account (or a GitHub App)
if PRs must show an identity distinct from the operator.
