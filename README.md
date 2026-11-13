# specfoundry

**Governed, least-privilege delivery for AI coding agents, on a laptop or in an enterprise
cluster.**

specfoundry takes a [Spec Kit](https://github.com/github/spec-kit) roadmap from an approved item
to a merged pull request.
- A deterministic gate decides what may start.
- Each worker runs isolated, without credentials.
- An independent grader judges the result, and a separate publisher opens a draft PR.
- A human merges, and an item counts as done only when the evidence says so.

> **Status: early and experimental.** The working name, interfaces and layout may change. See
> [the roadmap](.specify/memory/roadmap.md) for what is verified and what is planned.

## Why

Coding agents can write code. The hard part is trusting the process around them:
- Did the work start only when its dependencies were really done?
- Could the agent leak a credential?
- Who checked the result?
- Can a security team audit what happened afterwards?

specfoundry is built around those questions:

| Promise | How |
|---|---|
| **No worker starts on a blocked item** | `spec status` (from [spec-status](https://github.com/tosin2013/spec-status)) is the only gate, and it fails closed: blocked, missing or unreadable all mean *no* |
| **Workers never hold repository credentials** | One worker per pod and namespace, egress only through an allowlisting proxy, no service-account token. Only a separate publisher holds a token scoped to one repository |
| **Done means the evidence says so, not "CI passed"** | An independent grader in its own namespace (no secrets, no network) runs hidden acceptance tests. Every run writes an evidence record that can be audited offline |
| **Humans approve and merge** | Typed confirmations for the run mode, every retry and every status change. PRs are drafts, and nothing is merged automatically |
| **Laptop and enterprise** | Runs on kind with about 8 GB. Images are digest-pinned, run as any UID with a read-only root filesystem, and work through proxies and mirrored registries (OpenShift support is planned) |
| **No phone-home** | No third-party telemetry. Any first-party telemetry is operator observability sent only to your own collector |

## How it works

```text
roadmap.md ──► gate (spec status, fail closed) ──► mode confirmed by a human
                                                     │
          ┌──────────────────────────────────────────┘
          ▼
  worker attempt (own namespace, no SCM token, model-only egress, spend cap)
          │  change bundle via framed logs (no shared storage)
          ▼
  grader (own namespace, no secrets, no network, hidden tests) ── fail ──► retry? (human confirms)
          │ pass
          ▼
  publisher (only holder of a repo-scoped token) ──► draft PR ──► human merge
          │
          ▼
  reconcile ──► "verified" proposed ──► human approves ──► dependents unblock
```

## Status

| Milestone | Status | Evidence |
|---|---|---|
| **001** M0 isolation suite on kind + Calico | verified | [specs/001-m0-isolation-stub](specs/001-m0-isolation-stub/) (37/37 checks) |
| **002** M1 two-task gated pilot (plain Jobs) | verified | [run 20261113T030655Z](specs/002-m1-gated-pilot/evidence/20261113T030655Z/summary.md): A fails, B stays blocked, retry passes, 2 draft PRs, audit 11/11 |
| **003** Hardened GitHub-built images + Kelos comparison | in progress | [specs/003-m2-kelos-backend](specs/003-m2-kelos-backend/) |
| 004 GitHub loop · 005 OpenShift · 006 Operator guide | planned | [roadmap](.specify/memory/roadmap.md) |

## Try the pilot

The pilot runs a two-task fixture project (B depends on A) through the full lifecycle on a
local kind cluster: gate, isolated worker, independent grader, draft PR, your merge, approval,
then B. It takes about an hour on Ubuntu 24.04 (amd64) with Docker, a GitHub account and an
OpenAI-compatible model provider.

**Start here: [the operator guide](docs/operator-guide.md)**, which goes from a fresh
machine to an audited run, explaining every prompt. If something fails, see
[troubleshooting](docs/troubleshooting.md).

In short:

```sh
pilot/pilot publisher-token      # store and check the repo-scoped token (hidden prompt)
pilot/pilot up                   # kind + Calico, images pulled by digest, proxies, publisher namespace
pilot/pilot reset-fixture        # load the fixture into your throwaway repo
pilot/pilot run                  # confirm the mode; A/1 fails on purpose; confirm the retry; PR for A
#   ... review and merge A's draft PR on GitHub ...
pilot/pilot resume               # approve "A verified"; B runs; PR for B; audit
pilot/pilot down && pilot/pilot audit
```

Pilot reference: [pilot/README.md](pilot/README.md) · configuration contract:
[contracts/config.md](specs/002-m1-gated-pilot/contracts/config.md).

## How it's built

specfoundry is developed with its own method: every change starts as a Spec Kit spec, is
gated by `spec status`, and lands with evidence.

| Path | What |
|---|---|
| [`.specify/memory/constitution.md`](.specify/memory/constitution.md) | The project's non-negotiable principles |
| [`.specify/memory/roadmap.md`](.specify/memory/roadmap.md) | The roadmap: the only scheduling input |
| [`docs/prd.md`](docs/prd.md) | Product requirements |
| [`specs/`](specs/) | One folder per roadmap item: spec, plan, tasks, contracts, evidence |
| [`pilot/`](pilot/) | The pilot orchestrator (Python stdlib), images, manifests, fixture, hidden grading tests |
| [`test/isolation/`](test/isolation/) | The M0 isolation suite |
| [`.github/workflows/pilot-images.yml`](.github/workflows/pilot-images.yml) | Builds the digest-pinned images from verified upstream releases |

Run the unit tests with:

```sh
PYTHONPATH=pilot python3 -m unittest discover -s pilot/tests -t pilot
```

## How it compares

Agent runners such as [Kelos](https://github.com/kelos-dev/kelos) focus on running and
orchestrating agents conveniently. specfoundry focuses on the governed lifecycle around the
agent. A factual, cited comparison against our security bar is in
[specs/003-m2-kelos-backend/kelos-review.md](specs/003-m2-kelos-backend/kelos-review.md).

## Contributing

The project is early, so issues and discussion are welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the Spec Kit workflow, local checks and ground rules.
Report security problems privately through GitHub's vulnerability reporting.

## License

[Apache License 2.0](LICENSE). See also [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md).
