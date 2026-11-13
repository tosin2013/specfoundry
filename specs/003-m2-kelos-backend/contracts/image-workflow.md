# Contract: pilot image workflow (`.github/workflows/pilot-images.yml`)

## Triggers

- `push` to `main` touching `pilot/images/**`, `pilot/specfoundry_pilot/frame.py` or the
  input pins in `pilot/pins.env`; `pilot/images.lock` is excluded with a negated path filter
  (`!pilot/images.lock`), because GitHub forbids `paths` and `paths-ignore` on one event
- `workflow_dispatch` (manual)
- `pull_request` touching the same paths: **build only, no push**

## Matrix (registry is a parameter, FR-015c)

```yaml
target:
  - {registry: ghcr.io, namespace: tosin2013, variant: default}
  # 005 may add: {registry: quay.io, namespace: <org>, variant: openshift}
```

## Steps (per image: worker, tools, egress)

1. Read the input pins from `pilot/pins.env` (base digests, `OPENCODE_RELEASE`,
   `OPENCODE_ASSET_SHA256`, spec release and sha256).
2. **Worker:**
   - download `opencode-linux-x64.tar.gz` and `SHA256SUMS` from the pinned upstream release;
   - verify both the release's `SHA256SUMS` entry and the pinned `OPENCODE_ASSET_SHA256`;
   - **fail on any mismatch, with no fallback**.
3. **Tools:** download the pinned `spec` release asset and verify its sha256.
4. Build with the pinned base digests. Group-0 writable home and work dirs (arbitrary-UID
   friendly). Non-root, no sudo (the build asserts `! command -v sudo`).
   The worker image also gets `/kelos_entrypoint.sh` (FR-010).
   Smoke test: run each image with `--user 1000123:0 --read-only` (US2) before pushing.
5. Push to `<registry>/<namespace>/specfoundry-pilot-<image>`, tagged `sha-<commit>`, with
   `provenance: mode=max` and `sbom: true` (build-provenance attestation and SPDX SBOM), and
   resolve the digest. Packages are **public**.
6. Upload `image-digests.json` (see data-model.md).
7. Open (or update) a PR from branch `pilot-images/<commit>` that sets `WORKER_IMAGE`,
   `TOOLS_IMAGE` and `EGRESS_IMAGE` in **`pilot/images.lock`** (and no other file) to the new
   digests, with the commit message `chore(images): update digests [pilot-images]`. **Never
   push to `main` directly** (constitution V).

## No rebuild loop (analysis F1)

Docker builds aren't byte-reproducible, so a rebuild of unchanged inputs yields new digests.
The workflow therefore must never be triggered by its own output:
- **Inputs** (`pilot/pins.env`, `pilot/images/**`, `frame.py`) trigger builds and are never
  edited by the bot.
- **Output** (`pilot/images.lock`) is excluded from the trigger paths and is the only file the bot's PR may
  change. The PR job fails if its diff touches anything else.
- **Defence in depth:** jobs skip when the branch starts with `pilot-images/` or the head
  commit message contains `[pilot-images]`.

## Permissions

`contents: write` (only for the PR branch), `pull-requests: write`, `packages: write`.
No other secrets. The SCM publisher token and model keys are never available to this
workflow.

## Outputs consumed by `pilot up`

`pilot/images.lock` keys `WORKER_IMAGE`, `TOOLS_IMAGE`, `EGRESS_IMAGE` (digest references
only). Absent or tag-only values make `pilot up` stop, unless `--local-build` is given.
