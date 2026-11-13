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

## Configuring a provider for OpenCode

OpenCode reads providers from `opencode.json` and keys from files next to it. The pilot
mounts a directory you prepare as the worker's `~/.config/opencode` (read-only, a new
Secret per attempt, deleted with the attempt's namespace).

1. Create the directory:

   ```sh
   install -d -m 700 ~/.config/specfoundry/opencode
   ```

2. Put the key in `<provider>_api_key` (mode 600):

   ```sh
   install -m 600 /dev/null ~/.config/specfoundry/opencode/myprovider_api_key
   # then write the key into that file with your editor or secret manager
   ```

3. Write `~/.config/specfoundry/opencode/opencode.json` (mode 600). The `apiKey` **must be a
   file reference**, never the key itself (`pilot run` refuses literal keys). Example for any
   OpenAI-compatible endpoint:

   ```json
   {
     "$schema": "https://opencode.ai/config.json",
     "providers": {
       "myprovider": {
         "name": "My provider",
         "package": "@opencode/ai/providers/openai-compatible",
         "settings": {
           "baseURL": "https://api.example.com/v1",
           "apiKey": "{file:~/.config/opencode/myprovider_api_key}"
         },
         "models": {
           "my-model": {
             "name": "My model",
             "modelID": "my-model",
             "capabilities": {"tools": true, "input": ["text"], "output": ["text"]}
           }
         }
       }
     },
     "model": "myprovider/my-model"
   }
   ```

   If you already use OpenCode on the host, the same two files from `~/.config/opencode/`
   work as long as `apiKey` is a `{file:...}` reference.

4. In `~/.config/specfoundry/pilot.env` set:

   ```sh
   PILOT_MODEL=myprovider/my-model
   PILOT_MODEL_EGRESS_HOSTS=api.example.com   # host(s) of baseURL; the model proxy allowlist
   ```

5. Check it on the host first. With the same two files in `~/.config/opencode/`:

   ```sh
   opencode run --standalone --format json --model myprovider/my-model "Reply with ok"
   ```

   The `{file:~/...}` reference resolves against `$HOME`. In the worker, `$HOME` is
   `/home/worker`, and the directory is mounted at `/home/worker/.config/opencode`, so the
   same reference works in both places.

Things that did **not** work with OpenCode 2.2.7 in testing: passing the key through
environment variables (`{env:...}`, `OPENCODE_CONFIG_CONTENT`), and `opencode auth` (it
showed no credentials even when the host was configured).

## Spend caps

Every attempt has a cap (`PILOT_SPEND_CAP_USD`, default `1.00`), enforced in layers:

1. **Pilot watchdog (always):** sums `cost` and tokens from the harness's `step_finish`
   events and stops the harness at the cap.
   - If the provider reports a cost, the cap is in USD (`cap_mode: cost`).
   - Many OpenAI-compatible gateways report `cost: 0`. The watchdog then applies the token
     budget `PILOT_TOKEN_CAP` (default 2,000,000) and records `cap_mode: token-fallback`.
     A typical M1 attempt used about 190k-260k tokens.
   - To get USD accounting with such a gateway, declare prices on the model in
     `opencode.json` (per million tokens), so OpenCode computes `cost` itself:

     ```json
     "my-model": { "cost": { "input": 3.0, "output": 15.0 } }
     ```

2. **Provider-side cap (optional):** if your provider can limit a key's spend, set it and
   put `PILOT_PROVIDER_CAP_DECLARED=true` in `pilot.env` so the evidence records it.
3. **Deadline (always):** each worker Job has `activeDeadlineSeconds: 1200`.

The evidence record shows the cap, the mode and the observed spend for every attempt
(`attempts/<task>-<n>/report.json`), and the audit (AU06) fails a run that exceeded it.
