# Contract: docs check (`pilot/tools/docs_check.py`)

```sh
python3 pilot/tools/docs_check.py [FILE ...]    # default: docs/*.md README.md pilot/README.md
```

| Check | Rule | Failure message (example) |
|---|---|---|
| D1 commands | Every `pilot/pilot <sub> [--flag …]` in a fenced `sh`/`bash` block names a subcommand and flags that appear in `pilot/pilot --help` / `pilot/pilot <sub> --help` | `docs/operator-guide.md:212: unknown flag --force for 'reset-fixture'` |
| D2 paths | Every repo-relative path in a Markdown link or inline code that looks like a path (contains `/`, no spaces, no `<…>`, not a URL, not under `~`) exists in the repository | `docs/troubleshooting.md:40: missing path pilot/images/lock` |
| D3 versions | Versions quoted for kind, kubectl, Calico, spec and OpenCode equal `pilot/pins.env` (`KIND_VERSION`, `KUBECTL_VERSION`, `CALICO_VERSION`, `SPEC_VERSION`, `OPENCODE_VERSION`) | `README.md:88: kind v0.26.0 != pins v0.27.0` |
| D4 secrets | No match for the evidence redaction patterns (`specfoundry_pilot.audit.PATTERNS`) | `docs/operator-guide.md:301: token-like string` |

- **Exit codes:** 0 when all checks pass; 1 when any check fails (all failures listed); 2 on
  a usage or internal error.
- **Workflow:** `.github/workflows/docs-check.yml` runs on `pull_request` touching `docs/**`,
  `README.md`, `pilot/**` or the workflow itself. It uses `ubuntu-24.04`, Python 3.12, and
  actions pinned by SHA; it has no secrets and read-only `contents` permission.
- **Not covered here (done locally by the validator):** private provider names (listing them
  would publish them) and the exact text of quoted output.
