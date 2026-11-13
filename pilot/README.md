# specfoundry M1 pilot

The pilot drives one governed delivery cycle for a two-task fixture roadmap (A, then B, which
depends on A), held in a throwaway GitHub repo:

1. **Gate** (`spec status --json`, fail closed)
2. **Isolated worker** (OpenCode in a plain Kubernetes Job)
3. **Independent grader**
4. **Publisher** (the only holder of the SCM token; draft PRs only)
5. **Human merge**
6. **Reconcile and approve**, after which B unblocks

It proves that **no worker starts on a blocked item**. A's first attempt is made to fail on
purpose, B stays blocked through the failure and the retry, and B runs only after A is
verified.

- **Operators:** follow the [operator guide](../docs/operator-guide.md) ([troubleshooting](../docs/troubleshooting.md))
- Spec, plan and contracts: [`specs/002-m1-gated-pilot/`](../specs/002-m1-gated-pilot/)
- Step-by-step validation: [quickstart.md](../specs/002-m1-gated-pilot/quickstart.md)
- Harness and provider configuration: [docs/harnesses.md](../docs/harnesses.md)

## Prerequisites

- Docker, about 8 GB free RAM, Python 3.12, git, and `gh` logged in as you.
- `spec` 0.2.0 on the host (the gate runs there). The worker, tools and egress images are
  pulled by digest from `pilot/images.lock`; they are built by the
  [`pilot-images`](../.github/workflows/pilot-images.yml) workflow from verified upstream releases.
- An empty GitHub repo named `<anything>-pilot-fixture`, and a fine-grained token for
  **that repo only** (contents: write, pull requests: write).
- Operator configuration under `~/.config/specfoundry/`
  (see [contracts/config.md](../specs/002-m1-gated-pilot/contracts/config.md)):
  - `pilot.env`
  - `publisher.env`
  - `opencode/`

## Commands

```sh
pilot/pilot publisher-token # hidden prompt -> publisher.env (0600), then verify scope + expiry
pilot/pilot up              # kind + Calico (hash-checked), images by digest, proxies, publisher namespace
pilot/pilot up --local-build  # development: build pilot/images/ locally instead of pulling
pilot/pilot reset-fixture   # reset the throwaway repo to pilot/fixture/
pilot/pilot run             # gate, confirm mode, A attempts (confirm retries), publish A, pause
#   ... review and merge A's draft PR on GitHub ...
pilot/pilot resume          # reconcile (approve A -> verified), gate B, B attempts, publish B, audit
pilot/pilot down            # tear down and verify
pilot/pilot audit           # re-check the committed evidence (AU01-AU11)
pilot/pilot gate A|B [--root DIR]   # gate only (exit 0 allow, 10 refuse)
pilot/pilot status          # current run state
```

Every human decision is a typed `y`. Without a terminal, every prompt counts as **no**.

## Evidence

Each run writes `specs/002-m1-gated-pilot/evidence/<run-id>/`. Its layout is in
[contracts/evidence-record.md](../specs/002-m1-gated-pilot/contracts/evidence-record.md).
Commit it after `pilot down`.

## Tests

```sh
PYTHONPATH=pilot python3 -m unittest discover -s pilot/tests -t pilot -v
```

## Layout

| Path | What |
|---|---|
| `specfoundry_pilot/` | Orchestrator (Python stdlib only); `runner/` holds the pluggable runner (plain Jobs now; Kelos in 003) |
| `images/` | `worker` (OpenCode), `tools` (grader + publisher), `egress` (tinyproxy) |
| `manifests/` | Namespace, Job and proxy templates |
| `fixture/` | Template of the throwaway repo (roadmap 001 → 002, specs, visible tests) |
| `grading/` | Hidden acceptance tests: mounted only into grader namespaces |
| `tests/` | Unit tests, status fixtures, reference solution |
