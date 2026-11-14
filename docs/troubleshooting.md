# Troubleshooting

Each entry starts with what you see, then explains the cause, the fix and how to confirm the
fix. Entries are grouped by when they happen. The [operator guide](operator-guide.md) links
here from each step.

When you ask for help, never share your API key, your token, anything under
`~/.config/specfoundry/` or `~/.config/opencode/`, or your provider's hostname. See
[section 12 of the guide](operator-guide.md#12-when-something-goes-wrong) for what to share
instead.

## Index by symptom

| You see | Entry |
|---|---|
| `needs opencode.json and at least one <provider>_api_key file`, or the worker fails with HTTP 401 | [No API key file](#no-api-key) |
| `Cost (USD)` is `0.0` for every attempt | [Cost shows 0](#cost-zero) |
| `problem: token can write …: scope it to the fixture repo only` | [Token can write too much](#token-writes-project) |
| `problem: token rejected by GitHub (HTTP 401)` | [Token expired or revoked](#token-expired) |
| A prompt never appears, and the run exits 5 or pauses | [Prompts answer "no"](#prompts-answer-no) |
| `pilot up` fails while pulling images | [Image pull fails](#image-pull-error) |
| `Calico manifest hash mismatch` | [CNI hash mismatch](#cni-hash-mismatch) |
| `tagged reference not allowed` or `not a digest reference` | [Image pinned by tag](#tag-only-image) |
| `open pilot PRs exist on …` | [Open pilot PR left over](#open-pilot-pr) |
| `A's PR is not merged yet` | [Resume before merge](#resume-not-merged) |
| An attempt fails with reason `deadline` or `spend_cap` | [Deadline or spend cap](#deadline-or-spend-cap) |
| `GitHub Actions is not permitted to create or approve pull requests` | [Actions can't open PRs](#actions-cannot-open-prs) |
| `T01`, `T02` or `T03` fails after `pilot/pilot down` | [Leftovers after teardown](#leftovers) |

---

## Setup

<a id="no-api-key"></a>
### No API key file: "needs opencode.json and at least one <provider>_api_key file"

- **Symptom:**
  - `pilot/pilot up` or `run` stops with
    `~/.config/specfoundry/opencode needs opencode.json and at least one <provider>_api_key file`;
  - or the attempt's `report.json` shows the harness exited after an HTTP 401 from the model.
- **Cause:** OpenCode resolves `"apiKey": "{file:~/.config/opencode/<provider>_api_key}"`
  inside the worker. If the key file is missing, empty or wrongly named, the provider rejects
  the request.
- **Fix:** if OpenCode works on your machine, run `pilot/pilot import-opencode --force` to copy
  its setup again. Otherwise:
  1. Put the key, on one line, into `~/.config/specfoundry/opencode/<provider>_api_key`.
  2. Make sure `<provider>` matches the name in the `{file:...}` reference.
  3. Set modes: `chmod 700 ~/.config/specfoundry/opencode` and `chmod 600` on each file inside.
- **Confirm:** `pilot/pilot up` passes its config checks. The next attempt's `report.json`
  shows a harness exit of 0 and a non-zero token count.
- **Source:** the 002 live run setup (OpenCode returned 401 until the key file existed).

<a id="token-writes-project"></a>
### Token can write too much: "token can write …: scope it to the fixture repo only"

- **Symptom:** `pilot/pilot publisher-token` prints `publisher token: NOT OK`,
  `canary_push: True`, this problem line, and `not saved: …`. The token was thrown away.
- **Cause:** the token can push to the specfoundry repository you cloned from (the
  "canary"). That usually means a classic token, or a fine-grained token with *All
  repositories* access. The check is a real write test, not GitHub's permission labels, which
  describe your account rather than the token on public repositories.
- **Fix:** delete the token on GitHub. Create a fine-grained token with **Only select
  repositories** set to your fixture repo
  ([guide section 6](operator-guide.md#6-prepare-a-throwaway-fixture-repo-and-a-scoped-token)),
  then run `pilot/pilot publisher-token` again.
- **Confirm:** the output shows `repo_push: True` and `canary_push: False`.
- **Source:** commit 7570552 (the write probe replaced permission labels after the repo went
  public).

<a id="token-expired"></a>
### Token expired or revoked: "token rejected by GitHub (HTTP 401)"

- **Symptom:** `pilot/pilot publisher-token --check-only` (also run by `up`) prints
  `publisher token: NOT OK` and `problem: token rejected by GitHub (HTTP 401)`.
- **Cause:** the fine-grained token has expired, or it was deleted or regenerated on
  GitHub. The last check's `expires:` line shows when it would expire.
- **Fix:** generate a new token with the same settings, then run `pilot/pilot publisher-token`
  and paste it at the hidden prompt. The old `publisher.env` is replaced.
- **Confirm:** `pilot/pilot publisher-token --check-only` prints `publisher token: OK` with a
  future `expires:` date.
- **Source:** `pilot/images/tools/check_token.py`.

<a id="actions-cannot-open-prs"></a>
### Actions can't open PRs: "GitHub Actions is not permitted to create or approve pull requests"

This only affects you if you **fork specfoundry and run its image workflow** yourself.
Operators who pull the published images never see it.

- **Symptom:** the `pilot-images` workflow builds and pushes the images, but its last step
  fails with this message, so no PR updates `pilot/images.lock`.
- **Cause:** by default, GitHub doesn't let workflows open pull requests.
- **Fix:** in your fork, go to *Settings → Actions → General → Workflow permissions*, tick
  **Allow GitHub Actions to create and approve pull requests**, then re-run the failed job.
- **Confirm:** a PR titled `chore(images): update digests …` appears.
- **Source:** the first `pilot-images` run of 003 ([ci.md](../specs/003-m2-kelos-backend/evidence/ci.md)).

---

## Stand-up

<a id="image-pull-error"></a>
### Image pull fails during `pilot up`

- **Symptom:** `pilot/pilot up` stops after `== images`, with a Docker pull error such as
  `toomanyrequests`, `manifest unknown` or a network timeout.
- **Cause:**
  - the machine can't reach `ghcr.io`, for example because of a proxy or firewall;
  - or a rate limit was hit;
  - or `pilot/images.lock` names a digest that isn't published (only possible on an edited
    or unmerged branch).
- **Fix:**
  1. Check you can reach the registry: `docker pull hello-world`, then try one image from
     `pilot/images.lock` by hand.
  2. Behind a proxy, configure Docker's proxy (see
     [enterprise environments](harnesses.md#enterprise-environments)).
  3. Make sure you're on `main` with no local edits to the lock: `git status`.
  4. Run `pilot/pilot up` again.
- **Confirm:** the output reaches `== images: pulled by digest from pilot/images.lock` and
  `== up complete`.
- **Source:** 003 validation run `20261113T180203Z` (pull by digest).

<a id="cni-hash-mismatch"></a>
### CNI hash mismatch: "Calico manifest hash mismatch"

- **Symptom:** `pilot/pilot up` stops with
  `Calico manifest hash mismatch: expected <pinned>, got <actual>` and exits 2.
  Nothing has been applied to the cluster.
- **Cause:** the downloaded Calico manifest differs from the one pinned in
  `pilot/pins.env` (`CALICO_SHA256`). Either `pins.env` was edited, or the download was
  altered or truncated. The pilot never applies an unverified network plugin.
- **Fix:**
  1. Restore the pinned values: `git checkout pilot/pins.env`.
  2. Run `pilot/pilot down`, then `pilot/pilot up`.
  3. If it still fails on an untouched checkout, your network is altering the download.
     Don't work around it; open an issue.
- **Confirm:** `pilot/pilot up` completes, and the run's `versions.txt` lists `calico: <version>
  sha256=<pinned value>`.
- **Source:** 003 negative check (a wrong `CALICO_SHA256` exits 2 before applying anything).

<a id="tag-only-image"></a>
### Image pinned by tag: "tagged reference not allowed" or "not a digest reference"

- **Symptom:** `pilot/pilot up` or `run` stops with, for example,
  `WORKER_IMAGE in pilot/images.lock: tagged reference not allowed: '…:latest@sha256:…'`, or
  `not a digest reference`, and exits 2.
- **Cause:** every image must be referenced as `name@sha256:<64 hex>`, with no tag. A tag can
  be moved to different content later; a digest can't.
- **Fix:** restore the lock with `git checkout pilot/images.lock`. If you're mirroring images,
  write the mirror's `name@sha256:…` reference, which has the same digest (see
  [enterprise environments](harnesses.md#enterprise-environments)).
- **Confirm:** `pilot/pilot up` completes. Live check P10 passes during the run (every image
  pinned and non-root).
- **Source:** 003 negative check (a tag-only `WORKER_IMAGE` exits 2 before applying anything).

---

## Run time

<a id="prompts-answer-no"></a>
### Prompts answer "no": no question appears

- **Symptom:**
  - `pilot/pilot run` exits 5 without asking you to confirm the mode; or
  - it pauses at the retry (exit 6) without asking; or
  - `resume` exits 5 without showing the reconcile proposal's question.
- **Cause:** prompts are read from your terminal. Without one (an IDE task runner, CI,
  `nohup`, or piped input), every prompt is answered "no". This is deliberate: the pilot
  fails closed, so nothing proceeds without a human answer.
- **Fix:** run the command in a real interactive terminal, for example a plain SSH session.
  Then:
  - after exit 5 at the mode prompt, run `pilot/pilot run` again (nothing was started);
  - after a pause, run `pilot/pilot resume`.
- **Confirm:** you see `[y/N]` and can type `y`. `pilot/pilot status` shows the run moving on.
- **Source:** the 002 live run (a terminal-handling bug was fixed so prompts read the
  controlling terminal).

<a id="open-pilot-pr"></a>
### Open pilot PR left over: "open pilot PRs exist on …"

- **Symptom:** `pilot/pilot run` prints
  `open pilot PRs exist on <you>/<you>-pilot-fixture: [...]` and `run pilot reset-fixture first`,
  then exits 2.
- **Cause:** a previous run left draft PRs open. A new run won't start on top of them, so
  results can't mix.
- **Fix:** `pilot/pilot reset-fixture`, then type `y`. This force-resets the fixture repo and
  closes open `pilot/*` PRs.
- **Confirm:** `pilot/pilot run` gets past this check and shows the gate self-checks.
- **Source:** `pilot/specfoundry_pilot/pipeline.py` (pre-run check).

<a id="deadline-or-spend-cap"></a>
### Deadline or spend cap: an attempt fails with reason `deadline` or `spend_cap`

- **Symptom:** an attempt fails before grading. In `summary.md` its grade shows
  `fail (deadline)` or `fail (spend_cap)`. You're asked to confirm a retry, or the run fails
  with `<task>_RETRIES_EXHAUSTED` after the last retry.
- **Cause:**
  - **`deadline`:** the worker ran past its 20-minute limit. This usually means a slow or
    overloaded model endpoint.
  - **`spend_cap`:** the attempt reached `PILOT_SPEND_CAP_USD`, or `PILOT_TOKEN_CAP` when
    the provider reports no cost, and the watchdog stopped it.
- **Fix:**
  - Confirm the retry if the cause looks temporary.
  - For repeated `deadline` failures, try a faster model.
  - For repeated `spend_cap` failures, check the attempt's token count in `summary.md`. A
    reference attempt uses roughly 225,000–480,000 tokens. Raise the cap in
    `~/.config/specfoundry/pilot.env` only if you accept the cost.
  - After `RETRIES_EXHAUSTED`, start over with `pilot/pilot reset-fixture` and then
    `pilot/pilot run`.
- **Confirm:** a later attempt reaches grading. AU06 passes in the audit.
- **Source:** `pilot/specfoundry_pilot/worker.py` (failure reasons).

<a id="cost-zero"></a>
### Cost shows 0: `Cost (USD)` is `0.0` for every attempt

- **Symptom:** in `summary.md`, every attempt shows `0.0` cost but a large token count.
- **Cause:** your provider, like many OpenAI-compatible gateways, doesn't report a price.
  Nothing is wrong: the spend cap falls back to `PILOT_TOKEN_CAP` (2,000,000 tokens per
  attempt by default).
- **Fix (optional):** to cap in dollars, add per-million-token prices to the model in
  `opencode.json`, for example `"cost": {"input": 3.0, "output": 15.0}`, using your provider's
  real prices.
- **Confirm:** the next run's `summary.md` shows non-zero costs. AU06 still passes.
- **Source:** 002 and 003 runs (cost 0 from the gateway; the token fallback applied).

---

## Merge and resume

<a id="resume-not-merged"></a>
### Resume before merge: "A's PR is not merged yet"

- **Symptom:** `pilot/pilot resume` prints
  `A's PR is not merged yet. Merge it on GitHub, then run pilot resume again.` and exits 4.
- **Cause:** reconcile only proposes `A verified` after A's PR has actually merged. Nothing
  was changed.
- **Fix:** open the PR link printed by `run` (or check `pilot/pilot status`). Click **Ready for
  review**, then **Merge**, then run `pilot/pilot resume`.
- **Confirm:** `resume` shows the reconcile proposal and asks
  `Apply '001: planned → verified' to the fixture roadmap? [y/N]`.
- **Source:** `pilot/specfoundry_pilot/pipeline.py` (resume check).

---

## Teardown

<a id="leftovers"></a>
### Leftovers after teardown: T01, T02 or T03 fails

- **Symptom:** `pilot/pilot down` reports `FAIL T01 kind cluster deleted (present)`,
  `FAIL T02 … containers=<n>` or `FAIL T03 … containers=<n>`. The audit's AU07 then fails.
- **Cause:** a cluster or container survived deletion, often because Docker was busy or
  restarting.
- **Fix:** run `pilot/pilot down` again. If it still fails, remove the leftovers by hand:

  ```sh
  kind delete cluster --name specfoundry-m1
  docker ps -a --filter name=specfoundry-m1 --format '{{.Names}}'     # remove each with: docker rm -f <name>
  docker rm -f specfoundry-registry
  ```

  Then run `pilot/pilot down` once more, so the teardown checks are recorded.
- **Confirm:** T01–T03 all pass, and `pilot/pilot audit` shows AU07 passing.
- **Source:** `pilot/specfoundry_pilot/cluster.py` (teardown checks).
