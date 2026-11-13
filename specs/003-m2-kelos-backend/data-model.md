# Data Model: 003

All entities are files.

## Pilot image set (`pilot/pins.env` + workflow artifact `image-digests.json`)

| Key | Example / rule |
|---|---|
| `IMAGE_REGISTRY` | `ghcr.io/tosin2013` |
| `WORKER_IMAGE` | `ghcr.io/tosin2013/specfoundry-pilot-worker@sha256:…` |
| `TOOLS_IMAGE` | `ghcr.io/tosin2013/specfoundry-pilot-tools@sha256:…` |
| `EGRESS_IMAGE` | `ghcr.io/tosin2013/specfoundry-pilot-egress@sha256:…` |
| `OPENCODE_RELEASE` | `anomalyco/opencode@v2.2.7` |
| `OPENCODE_ASSET_SHA256` | sha256 of `opencode-linux-x64.tar.gz` (must also match the release's `SHA256SUMS`) |
| `SPEC_SHA256` | already present (002); the tools build verifies against it |
| `CALICO_SHA256` | the pinned manifest hash (FR-007) |

Rule: every `*_IMAGE` matches `^[a-z0-9./-]+@sha256:[0-9a-f]{64}$`. `pilot up` refuses
anything else unless `--local-build` is given.

`image-digests.json` (workflow artifact):
`{commit, built_at, registry, images: {worker, tools, egress}, inputs: {opencode:
{release, asset, sha256}, spec: {sha256}, bases: {debian, alpine}}}`.

## Image source (in `run.json` and `versions.txt`)

| Field | Values |
|---|---|
| `image_source` | `pinned` (pulled by digest from the registry) / `local-build` |
| `images` | the three digest references actually used |

## Competitive review (`kelos-review.md`)

| Field | Notes |
|---|---|
| `kelos_version`, `kelos_commit` | `v0.64.0`, `83a7405860df50e91e3313eb63b8e22f244fd943` |
| `specfoundry_commit` | the commit compared |
| `security_bar[SB-1..SB-8]` | for each product: a factual description plus a citation (path:line, doc section, probe ID or evidence path), or `unverified` |
| `capabilities[]` | `{name, kelos: description+citation, specfoundry: have/gap/won't do, constraint_to_keep}` (≥ 5 items) |
| `probes[]` | optional `{id, what, how, observed}` on a throwaway cluster |
| `attribution` | ideas borrowed from Kelos, with links |
