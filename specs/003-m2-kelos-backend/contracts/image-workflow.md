# Contract: pilot image workflow (`.github/workflows/pilot-images.yml`)

## Triggers

- `push` to `main` touching `pilot/images/**`, `pilot/specfoundry_pilot/frame.py` or the
  input pins in `pilot/pins.env`
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
5. Push to `<registry>/<namespace>/specfoundry-pilot-<image>`, tagged `sha-<commit>`, and
   resolve the digest. Packages are **public**.
6. Upload `image-digests.json` (see data-model.md).
7. Open (or update) a PR from branch `pilot-images/<commit>` that sets `WORKER_IMAGE`,
   `TOOLS_IMAGE` and `EGRESS_IMAGE` in `pilot/pins.env` to the new digests. **Never push
   to `main` directly** (constitution V).

## Permissions

`contents: write` (only for the PR branch), `pull-requests: write`, `packages: write`.
No other secrets. The SCM publisher token and model keys are never available to this
workflow.

## Outputs consumed by `pilot up`

`pilot/pins.env` keys `WORKER_IMAGE`, `TOOLS_IMAGE`, `EGRESS_IMAGE` (digest references
only). Absent or tag-only values make `pilot up` stop, unless `--local-build` is given.
