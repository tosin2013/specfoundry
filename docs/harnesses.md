# Worker harnesses and model providers

The pilot's worker runs a coding **harness** (an agent CLI) against a **model provider**.
Both are configuration: the pilot does not prefer a provider, and the harness sits behind
one worker contract (`specs/002-m1-gated-pilot/contracts/worker-io.md`): read `/in`, work in
a scratch workspace, emit one result frame on stdout.

## Harness options

| Harness | Status in specfoundry | What the worker needs | Headless run | Spend signal |
|---|---|---|---|---|
| **OpenCode** | Used in M1 (v2.2.7) | the `opencode` binary; its config dir (`opencode.json` + key file) | `opencode run --standalone --format json --auto --model <provider>/<model> "<prompt>"` | `step_finish` events carry `cost` and `tokens` |
| Claude Code | Later (not yet verified here) | the `claude` binary; an API key or provider config | `claude -p "<prompt>" --output-format stream-json` | result events carry usage and cost |
| Codex CLI | Later (not yet verified here) | the `codex` binary; an API key | `codex exec --json "<prompt>"` | usage events |
| GitHub Copilot CLI | Later (not yet verified here) | the `copilot` binary; a Copilot token | non-interactive prompt mode | provider-side usage only |

The "later" rows are starting points from each tool's documentation. Verify the exact
flags against the pinned version before adding a harness.

Rules that apply to every harness (constitution IV, PRD S2/S6):

- The image is thin, non-root, without sudo, and pinned by digest; the binary is verified
  by sha256 at build time (`pilot/pins.env`).
- The harness never holds an SCM credential. Its egress is limited to the model host(s)
  through the model egress proxy.
- Its own output goes to files, never to stdout (stdout is reserved for the result frame).

## How the worker image packages OpenCode

The worker image is built by GitHub Actions (`.github/workflows/pilot-images.yml`), never
from an operator's machine:
- OpenCode comes from the upstream release named in `pilot/pins.env` (`OPENCODE_RELEASE`).
- The build verifies the archive against the release's `SHA256SUMS` **and** the pinned
  `OPENCODE_ASSET_SHA256`, then checks the extracted binary against `OPENCODE_SHA256`. A
  mismatch fails the build, with no fallback.
- Images are published as public packages, and `pilot up` pulls them by the digests in
  `pilot/images.lock`. `pilot up --local-build` builds the same Dockerfiles locally for
  development.

Update checks, model-catalogue fetches and free-model discovery are switched off in the
image (`OPENCODE_DISABLE_AUTOUPDATE`, `OPENCODE_DISABLE_MODELS_FETCH`,
`OPENCODE_DISABLE_FREE_MODELS`).

### Enterprise environments

- **Arbitrary UID:** the images run under any assigned user ID with group 0 and a read-only
  root filesystem (OpenShift's restricted SCC model). `pilot/images/smoke.sh` checks this in
  CI on every build.
- **Proxies:** the worker reaches its model only through `HTTPS_PROXY`. Point it at your
  corporate proxy, or at the pilot's allowlisting egress proxy.
- **Mirrored or air-gapped registries:** copy the images by digest into your registry and
  point `pilot/images.lock` at the copies. The digests don't change.
- **Kelos users:** the worker image also provides `/kelos_entrypoint.sh`, a compatibility shim
  so it can run where Kelos's agent-image contract is expected. specfoundry itself does not
  use or depend on Kelos.

## Configuring a model provider

Provider setup for the default harness (OpenCode), spend caps and price declarations are in
[providers.md](providers.md). The quickest path, if you already use OpenCode, is
`pilot/pilot import-opencode`.
