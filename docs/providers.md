# Model providers

The pilot's worker runs **OpenCode** (v2.2.7, pinned in `pilot/pins.env`). OpenCode is the
default and the only harness supported in this release; other harnesses are listed in
[harnesses.md](harnesses.md). This page covers which model providers work and how to
configure one.

The pilot doesn't prefer a provider. It needs only:
- an endpoint OpenCode can talk to, such as any **OpenAI-compatible** API;
- a model that supports **tool calling**, since the agent edits files and runs tests through
  tools;
- a host name the worker can reach over HTTPS. Workers can connect **only** to the hosts in
  `PILOT_MODEL_EGRESS_HOSTS`, through the allowlisting egress proxy;
- an API key kept in a **file**, never in `opencode.json` itself.

## Where the configuration lives

```text
~/.config/specfoundry/
├── pilot.env                  # PILOT_MODEL, PILOT_MODEL_EGRESS_HOSTS, caps, fixture repo
└── opencode/                  # mode 700; mounted as the worker's ~/.config/opencode
    ├── opencode.json          # mode 600; providers, models, default model
    └── <provider>_api_key     # mode 600; the key, one line
```

For each attempt, the pilot copies `opencode/` into a new Kubernetes Secret, mounts it
read-only at `/home/worker/.config/opencode`, and deletes it with the attempt's namespace.
Only files named `opencode.json` and `*_api_key` are copied.

## Option A: you already use OpenCode

If OpenCode already works on your machine, reuse its setup:

```sh
pilot/pilot import-opencode --fixture-repo <you>/<you>-pilot-fixture
```

```text
imported OpenCode config: ~/.config/opencode -> ~/.config/specfoundry/opencode
  model: <provider>/<model>
  key files: <provider>_api_key
wrote ~/.config/specfoundry/pilot.env (model, its egress host, default caps)
```

What it does:
- **Copies only what the worker needs:** the provider of your default `"model"` (choose
  another with `--model <provider>/<model>`), and that provider's key file. Other
  providers, MCP servers, plugins and other settings are left out, and the output lists
  them. The worker couldn't reach them anyway.
- **Writes `pilot.env`** with the model and its egress host, if you don't have one yet. If you
  do, it leaves the file unchanged and tells you what doesn't match. It never prints the
  host or the key.
- **Refuses unsafe or unworkable configs:**
  - a literal key: move it into `~/.config/opencode/<provider>_api_key` and reference it as
    `"{file:~/.config/opencode/<provider>_api_key}"`;
  - an `{env:...}` reference: the worker can't see your shell's environment;
  - a key file outside `~/.config/opencode/`, or one not named `*_api_key`.
- **Won't overwrite** an existing worker config unless you pass `--force`.

Your host OpenCode version may differ from the worker's (v2.2.7). If the worker fails on
config that works on your machine, compare against the format in option B.

## Option B: write it by hand

1. Create the directory and the key file:

   ```sh
   install -d -m 700 ~/.config/specfoundry/opencode
   install -m 600 /dev/null ~/.config/specfoundry/opencode/myprovider_api_key
   # then write the key into that file with your editor or secret manager
   ```

2. Write `~/.config/specfoundry/opencode/opencode.json` (mode 600). This works for any
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

   The path says `~/.config/opencode/...`, not `specfoundry`, on purpose. In the worker,
   `$HOME` is `/home/worker` and the directory is mounted at `/home/worker/.config/opencode`,
   so the same reference works on your machine and in the worker.

3. In `~/.config/specfoundry/pilot.env` (mode 600) set:

   ```sh
   PILOT_MODEL=myprovider/my-model
   PILOT_MODEL_EGRESS_HOSTS=api.example.com   # the host of baseURL; comma-separate several
   ```

4. Optional: check it on your machine first. With the same two files in `~/.config/opencode/`:

   ```sh
   opencode run --standalone --format json --model myprovider/my-model "Reply with ok"
   ```

## Kinds of provider

| Provider | Status | Notes |
|---|---|---|
| **OpenAI-compatible gateway or hosted API** (`openai-compatible` package) | **Verified** in the 002 and 003 runs | Use option A or B. Many gateways report a cost of 0, so the cap falls back to tokens (see below). |
| Enterprise gateway behind a corporate proxy | Partly verified (003: proxy-only egress) | Same as above. See [enterprise environments](harnesses.md#enterprise-environments). |
| OpenCode's built-in provider packages for specific vendors | Not yet verified here | Should work if the key is a `{file:...}` reference and the API host is in `PILOT_MODEL_EGRESS_HOSTS`. Check package names in OpenCode's own docs. |
| Self-hosted endpoint (an OpenAI-compatible server you run) | Not yet verified here | Needs a host name that pods in the kind cluster can resolve and reach; `localhost` on your machine doesn't work from inside the cluster. |

Things that did **not** work with OpenCode 2.2.7 in testing:
- passing the key through environment variables (`{env:...}`, `OPENCODE_CONFIG_CONTENT`);
- `opencode auth`, which showed no credentials even on a configured machine.

## Spend caps

Every attempt has a cap (`PILOT_SPEND_CAP_USD`, default `1.00`), enforced in layers:

1. **Pilot watchdog (always):** adds up `cost` and tokens from OpenCode's `step_finish`
   events, and stops the harness at the cap.
   - If the provider reports a cost, the cap is in USD (`cap_mode: cost`).
   - If it reports a cost of 0, as many OpenAI-compatible gateways do, the watchdog applies
     the token budget `PILOT_TOKEN_CAP` (default 2,000,000) instead, and records
     `cap_mode: token-fallback`. Reference attempts used about 225,000–480,000 tokens.
   - To get USD accounting through such a gateway, declare the model's prices (USD per
     million tokens) in `opencode.json`, so OpenCode computes `cost` itself:

     ```json
     "my-model": { "cost": { "input": 3.0, "output": 15.0 } }
     ```

2. **Provider-side cap (optional):** if your provider can limit a key's spend, set that
   limit, and put `PILOT_PROVIDER_CAP_DECLARED=true` in `pilot.env` so the evidence records it.
3. **Deadline (always):** each worker Job is stopped after 1200 seconds.

The evidence shows the cap, its mode and the observed spend for every attempt
(`attempts/<task>-<n>/report.json`). The audit's AU06 check fails any run that went over its
cap.

## Problems

See [troubleshooting](troubleshooting.md), especially
[No API key file](troubleshooting.md#no-api-key) and
[Cost shows 0](troubleshooting.md#cost-zero).
