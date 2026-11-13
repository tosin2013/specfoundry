# Contributing to specfoundry

Thanks for your interest. specfoundry is early and experimental, so issues, questions and
design discussion are as welcome as code.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ground rules

specfoundry is built with its own method, so a few rules are firmer than usual. They come
from the [constitution](.specify/memory/constitution.md):

- **The roadmap is the source of truth.** Work is scheduled only from
  [`.specify/memory/roadmap.md`](.specify/memory/roadmap.md). A new feature starts as a roadmap
  entry and then a spec, not as a drive-by PR.
- **Gates fail closed.** Never weaken the gate, retry confirmations or human approvals to make
  something pass.
- **Least privilege.** Workers never hold SCM credentials; only the publisher does. Don't add
  credentials, broad RBAC or cluster-wide controllers to the worker path.
- **Evidence, not CI, defines done.** A change that affects pilot behaviour needs a pilot run
  whose evidence and audit pass.
- **No secrets anywhere.** Never commit keys, tokens, provider hostnames or operator
  configuration. The evidence redaction scan and the audit must stay clean.

## Ways to contribute

- **Report a bug or ask a question:** open an issue with what you ran, what you expected and
  what happened. Include `pilot/pilot status` output and redacted logs. Never include tokens
  or keys.
- **Propose a feature:** open an issue describing the outcome you want. If it fits, it becomes
  a roadmap entry.
- **Report a security problem:** use GitHub's **private vulnerability reporting** (the
  repository's *Security* tab), not a public issue.

## Development workflow

Changes follow [Spec Kit](https://github.com/github/spec-kit):

1. **Roadmap:** the item exists in `.specify/memory/roadmap.md` (added with
   `/speckit-roadmap-write`).
2. **Spec:** `/speckit-specify` (and `/speckit-clarify` if needed).
3. **Plan:** `/speckit-plan`, including the constitution check.
4. **Tasks:** `/speckit-tasks`, then `/speckit-analyze`. Resolve CRITICAL and HIGH findings
   first.
5. **Implement:** `/speckit-implement`, marking tasks done as you go.
6. **Close:** `/speckit-roadmap-debrief`, then a status change via `/speckit-roadmap-write`.
   Status is recorded `verified` only on evidence.

`spec status` (from [spec-status](https://github.com/tosin2013/spec-status)) must parse the
roadmap cleanly at every step.

### Local checks

```sh
PYTHONPATH=pilot python3 -m unittest discover -s pilot/tests -t pilot   # unit tests (stdlib only)
spec status                                                             # roadmap parses, gates hold
```

For image changes (`pilot/images/**`), also run the arbitrary-UID smoke test against local
builds:

```sh
pilot/pilot up --local-build      # or build the images yourself
WORKER=<ref> TOOLS=<ref> EGRESS=<ref> pilot/images/smoke.sh
```

### Style

- **Orchestrator (`pilot/specfoundry_pilot/`):** Python 3.12, standard library only; external
  tools are called as subprocesses.
- **Images:** thin, non-root, no sudo, upstream inputs verified by checksum, runnable as any
  UID with a read-only root filesystem. Pins live in `pilot/pins.env`; image digests in
  `pilot/images.lock` are updated only by the `pilot-images` workflow's PR.
- **Docs:** plain, factual language. Comparisons with other projects cite sources and stay
  neutral.

## Pull requests

- Keep PRs focused on one roadmap item or task group, and link the spec.
- Include test results, and evidence links for pilot-affecting changes.
- PRs need a human review and merge; nothing in this project auto-merges.

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), the project's licence.
