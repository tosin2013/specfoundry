# specfoundry operator guide: repeat the pilot from zero

This guide takes you from a fresh Linux machine to a completed, audited run of the specfoundry
pilot. Follow it top to bottom. If anything fails, the matching entry in
[troubleshooting](troubleshooting.md) explains why and how to fix it.

**Contents:**
1. [What you'll do](#1-what-youll-do)
2. [How specfoundry keeps you safe](#2-how-specfoundry-keeps-you-safe)
3. [Before you start](#3-before-you-start)
4. [Install the tools](#4-install-the-tools)
5. [Configure your model provider](#5-configure-your-model-provider)
6. [Prepare a throwaway fixture repo and a scoped token](#6-prepare-a-throwaway-fixture-repo-and-a-scoped-token)
7. [Stand up](#7-stand-up)
8. [Run the pilot, every prompt explained](#8-run-the-pilot-every-prompt-explained)
9. [The merge pause, then resume](#9-the-merge-pause-then-resume)
10. [Read the evidence and the audit](#10-read-the-evidence-and-the-audit)
11. [Tear down and confirm](#11-tear-down-and-confirm)
12. [When something goes wrong](#12-when-something-goes-wrong)
13. [What will change](#13-what-will-change)

---

## 1. What you'll do

You'll run a small, fully governed delivery cycle on your own machine. A throwaway project
has two tasks: **A** (a slug function) and **B** (a unique-slug function that depends on A).
The pilot shows that:
- B can't start until A is verified;
- workers never hold your GitHub token;
- an independent grader judges each attempt;
- only you merge.

```text
 stand up ─► gate A ✔ / gate B ✘ ─► A attempt 1 (fails on purpose) ─► you confirm a retry
   ─► A attempt 2 passes ─► draft PR for A ─► YOU merge it ─► you approve "A verified"
   ─► gate B ✔ ─► B passes ─► draft PR for B ─► audit ─► tear down
```

**When you're done** you'll have a passing audit (11 of 11 checks), two draft PRs on your
throwaway repo (one merged by you), a verified teardown, and an evidence folder you can
inspect.

**Your part:** two `y` answers (run mode, retry), one PR merge on GitHub, and one `y` to
approve a status change.

**Time:** about 60 minutes hands-on, plus downloads and about 10 minutes of model work.

---

## 2. How specfoundry keeps you safe

Read this first if you're evaluating specfoundry. Every guarantee below is checked on every
run, and the check IDs appear in your evidence (section 10).

| Guarantee | How | Proof in your run |
|---|---|---|
| **No work starts on a blocked item** | A deterministic gate (`spec status`) decides; anything blocked, missing or unreadable means *no* | GM01–GM04 (gate self-checks), AU01 (B refused until A verified), AU05 |
| **Workers never hold a repository credential** | One worker per pod and namespace; only the publisher's namespace holds the token | P04, P09, AU04 |
| **Workers can only reach the model** | Default-deny network plus an allowlisting egress proxy | P06; `proxy-denials.log` shows what was refused |
| **An independent grader judges the work** | A separate namespace with no secrets and no network, running hidden acceptance tests | P07, P08; checks G1–G5 in each `grade.json` |
| **Only the publisher opens PRs, and only as drafts** | The publisher Job is the only token holder, and has no merge path | AU03 |
| **Humans decide** | You confirm the mode, every retry, the merge and the status change | AU09, AU10; the reconcile prompt |
| **The induced failure is honest** | Only attempt A/1 has its acceptance details withheld | AU11 |
| **Spend is capped** | $1 per attempt, or a token budget when the provider reports no cost | AU06 |
| **No phone-home** | No third-party telemetry; nothing leaves your machine except model traffic and GitHub calls you configured | Constitution C-10; `proxy-denials.log` |
| **Pinned, verifiable images** | Public images built by GitHub from checksum-verified sources, with provenance and an SBOM, pulled only by digest | P10; `pilot/images.lock`; [image CI evidence](../specs/003-m2-kelos-backend/evidence/ci.md) |
| **The checks aren't vacuous** | Removing the network policies or planting a credential makes them fail | [mutation test](../specs/002-m1-gated-pilot/evidence/20261113T030655Z/mutation.md) |

### Known limits today

- **PRs show your account as author.** A fine-grained token belongs to a person. A GitHub App
  identity is planned (roadmap 004).
- **Spend caps may run on tokens.** Many OpenAI-compatible gateways report a cost of 0, so the
  cap applies to tokens (default 2,000,000 per attempt). See section 5 to declare prices.
- **The gate runs on your machine**, not in the cluster (there's no spec-status container
  image yet).
- **Your provider key is long-lived.** It's copied into a fresh Secret for each attempt and
  deleted with it. Per-run keys are planned for 005.
- **Single-node kind only, and Linux only** (section 13).

For a cited comparison with another agent runner, see the
[Kelos review](../specs/003-m2-kelos-backend/kelos-review.md). For mirroring images into
your own registry and running behind a corporate proxy, see
[enterprise environments](harnesses.md#enterprise-environments).

---

## 3. Before you start

You need:
- **A machine:** Ubuntu 24.04 LTS on amd64, 4+ CPU cores, 8 GB of free RAM, 30 GB of free
  disk. A VM is fine.
- **A GitHub account.**
- **A model provider** with an OpenAI-compatible endpoint, and an API key for it.

> **macOS is not supported yet.** The pilot's images are built for amd64 only; Apple Silicon
> needs multi-architecture images, which are planned (section 13).

If something in this guide fails, see [troubleshooting](troubleshooting.md).

---

## 4. Install the tools

**Docker Engine.** Follow Docker's official
[Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/), which are summarised
here:

```sh
sudo apt-get update && sudo apt-get install -y ca-certificates curl git python3
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
sudo usermod -aG docker "$USER"     # then log out and back in
```

**GitHub CLI.** Install it with the official
[instructions for Debian/Ubuntu](https://github.com/cli/cli/blob/trunk/docs/install_linux.md),
then sign in:

```sh
gh auth login          # GitHub.com → HTTPS → authenticate in the browser
```

**spec 0.2.0** ([spec-status](https://github.com/tosin2013/spec-status)), the gate.
Verify the checksum before installing:

```sh
mkdir -p ~/.local/bin /tmp/spec && cd /tmp/spec
gh release download v0.2.0 -R tosin2013/spec-status -p 'spec_0.2.0_linux_amd64.tar.gz' -p 'spec_0.2.0_checksums.txt'
sha256sum -c --ignore-missing spec_0.2.0_checksums.txt          # must print: ... OK
tar -xzf spec_0.2.0_linux_amd64.tar.gz && install -m 0755 spec_0.2.0_linux_amd64/spec ~/.local/bin/spec
cd ~
```

If `~/.local/bin` isn't on your `PATH` yet, log out and back in (Ubuntu adds it when it exists).

**The project:**

```sh
git clone https://github.com/tosin2013/specfoundry.git
cd specfoundry
```

You don't need to install kind or kubectl. `pilot/pilot up` installs the pinned
kind v0.27.0 and kubectl v1.32.2 into `~/.local/bin`, verifying their checksums.

**Check everything** before moving on:

```sh
docker run --rm hello-world && gh auth status && spec --version && python3 --version
```

You should see Docker's hello message, `Logged in to github.com`, `spec 0.2.0`, and
`Python 3.12.x`.

---

## 5. Configure your model provider

The worker runs [OpenCode](https://github.com/anomalyco/opencode), the default and only
harness in this release, against your model provider. Any OpenAI-compatible endpoint with a
tool-calling model works. This step creates two things under `~/.config/specfoundry/`:
- **`opencode/`:** OpenCode's config plus your API key, kept in a separate file;
- **`pilot.env`:** the pilot's settings. Every `pilot/pilot` command reads this file, so it
  comes first.

**First, choose your fixture repo's name.** It must end in `-pilot-fixture`, for example
`<you>-pilot-fixture`. You'll create the repo in section 6.

### If you already use OpenCode

```sh
pilot/pilot import-opencode --fixture-repo <you>/<you>-pilot-fixture
```

```text
imported OpenCode config: ~/.config/opencode -> ~/.config/specfoundry/opencode
  model: <provider>/<model>
  key files: <provider>_api_key
wrote ~/.config/specfoundry/pilot.env (model, its egress host, default caps)
```

This copies only your default model's provider and its key file, and writes `pilot.env`. It
never prints your key or your provider's host. It refuses a config with a literal key or an
`{env:...}` reference, and the error tells you how to fix it. Details and options:
[providers.md](providers.md#option-a-you-already-use-opencode).

Then continue to section 6.

### Otherwise, write it by hand

```sh
install -d -m 700 ~/.config/specfoundry/opencode
install -m 600 /dev/null ~/.config/specfoundry/opencode/myprovider_api_key
install -m 600 /dev/null ~/.config/specfoundry/opencode/opencode.json
# now put your API key into myprovider_api_key with an editor (one line, no quotes)
```

Edit `~/.config/specfoundry/opencode/opencode.json`, using your provider's URL and model. The
`apiKey` **must** be a file reference, never the key itself; the pilot refuses literal keys.

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

The path says `~/.config/opencode/...`, not `specfoundry`, on purpose: inside the worker,
this directory is mounted as OpenCode's own config directory.

Then create `~/.config/specfoundry/pilot.env`:

```sh
install -m 600 /dev/null ~/.config/specfoundry/pilot.env
cat > ~/.config/specfoundry/pilot.env <<'EOF'
PILOT_FIXTURE_REPO=<you>/<you>-pilot-fixture
PILOT_FIXTURE_BRANCH=main
PILOT_MODEL=myprovider/my-model
PILOT_MODEL_EGRESS_HOSTS=api.example.com
PILOT_SPEND_CAP_USD=1.00
PILOT_TOKEN_CAP=2000000
PILOT_PROVIDER_CAP_DECLARED=false
EOF
```

### Either way

- **`PILOT_MODEL_EGRESS_HOSTS`** is the host from your `baseURL`. It's the only place workers
  may connect to. The evidence records only a hash of it.
- **Spend:** if your provider reports no cost (many gateways don't), the cap runs on tokens.
  To get a cap in dollars, declare your model's prices; see
  [providers.md](providers.md#spend-caps).
- **Other providers**, such as vendor-specific packages or a self-hosted endpoint, are
  covered in [providers.md](providers.md).

---

## 6. Prepare a throwaway fixture repo and a scoped token

The pilot works on a **throwaway repository** that it force-resets at the start of each run.
Never point it at a repository you care about.

1. **Create the fixture repo.** On GitHub, create a new, **empty** repository (no README,
   licence or .gitignore), with the name you put in `PILOT_FIXTURE_REPO` in section 5.
   Public or private both work.
2. **Create a fine-grained token for that repo only.** On GitHub go to
   *Settings → Developer settings → Fine-grained tokens → Generate new token*:
   - **Repository access:** *Only select repositories* → your fixture repo.
   - **Permissions:** *Contents* read and write; *Pull requests* read and write. *Metadata*
     read-only is added automatically.
   - **Expiration:** short, for example 7–30 days.
3. **Store and check it.** The token goes through a hidden prompt straight into a 0600 file.
   It never appears on screen, in shell history or in logs.

```sh
pilot/pilot publisher-token
```

```text
from run 20261113T180203Z (token check)
publisher token: OK
  login: tosin2013
  repo: tosin2013/craz3-pilot-fixture
  repo_push: True
  canary: tosin2013/specfoundry
  canary_push: False
  expires: 2026-12-13 02:58:52 UTC
```

What each line means:
- **`repo_push: True`:** the token can write your fixture repo. That's required.
- **`canary_push: False`:** the token can **not** write the project's own repository. That
  proves it's scoped narrowly. Both results come from a real write test, an invisible
  unreferenced blob, not from GitHub's permission labels.
- **`expires`:** when you'll need a new token.

**Why the scope matters.** Only the *publisher* ever holds this token; workers never see it.
Even so, a token that can write only a throwaway repo limits the damage if anything goes
wrong. Until roadmap item 004, PRs will show your account as their author.

---

## 7. Stand up

```sh
pilot/pilot up
```

This:
- re-checks your token;
- installs the pinned kind and kubectl;
- creates a kind cluster with Calico (refusing to apply Calico unless its hash matches the
  pinned value);
- pulls the pilot images **by digest** from `pilot/images.lock`;
- starts the two egress proxies and the publisher namespace.

It takes 3–6 minutes the first time and ends with:

```text
== images: pulled by digest from pilot/images.lock
== egress proxies
== publisher namespace
== check helpers
== up complete
```

Next, load the fixture into your throwaway repo. This **force-resets that repo only**; the
command refuses any repo whose name doesn't end in `-pilot-fixture`.

```sh
pilot/pilot reset-fixture        # type y to confirm
```

```text
fixture reset: <you>/<you>-pilot-fixture@main = <commit>
```

Optionally, see the gate decide before anything runs:

```sh
pilot/pilot gate A               # "decision": "allow", exit 0
pilot/pilot gate B               # "decision": "refuse", "DEP_UNSATISFIED:001", exit 10
```

If stand-up fails, see [troubleshooting](troubleshooting.md#stand-up).

---

## 8. Run the pilot, every prompt explained

Run this **in a real terminal**. Prompts read from your terminal, so if there's none (for
example inside some IDE runners or CI), every answer counts as "no".

```sh
pilot/pilot run
```

The output below is from the real run `20261113T180203Z`; its full transcript is
[console.txt](../specs/003-m2-kelos-backend/evidence/20261113T180203Z/console.txt).

**First, the gate checks itself and decides:**

```text
from run 20261113T180203Z
  PASS GM01  FR-002   gate unit matrix (all refusal cases refuse)
  PASS GM02  FR-002   missing roadmap refuses
  PASS GM03  FR-002   status tool error refuses
  PASS GM04  FR-002   truncated roadmap refuses B
  gate A: allow ['OK']
  gate B: refuse ['DEP_UNSATISFIED:001']
```

GM01–GM04 prove the gate refuses broken input. A is allowed; B is refused because it depends
on A.

**Prompt 1: the run mode.**

```text
from run 20261113T180203Z
Run mode for this pilot: {"name": "step-by-step", "retry_limit": 2, "spend_cap_usd": 1.0, "token_cap": 2000000, "worker_deadline_s": 1200}
  one attempt at a time; every retry needs your confirmation; risk rating is out of scope in M1.
Confirm this mode and start staging workers? [y/N]
```

Type `y`. This means: one attempt at a time; at most 2 retries; a $1 (or 2M-token) cap per
attempt; 20 minutes per worker. If you answer `N`, nothing is started and the command exits
with code 5.

**Attempt A/1 fails on purpose.** The first attempt is given the task *without* its
"Acceptance details" section, so it can't know the exact rules the hidden tests check. It
fails grading on G5 (the hidden tests). That shows a failed grade keeps B blocked. While each
worker runs, live checks confirm its isolation:

```text
from run 20261113T180203Z
  PASS P01   FR-005   worker namespace has exactly 1 pod with 1 container
  PASS P02   FR-006   SA and pod automount off; no token file
  ...
  PASS P08   FR-010   worker SA cannot create/patch/exec in its grader namespace
  gate B: refuse ['DEP_UNSATISFIED:001']
```

**Prompt 2: retry.**

```text
from run 20261113T180203Z
Retry A (attempt 2 of 3)? [y/N]
```

Type `y`. If you answer `N`, the run pauses (exit 6), and `pilot/pilot resume` asks again
later.

**Attempt A/2 passes, and the publisher opens a draft PR.** Two more checks confirm only the
publisher holds the token (P09) and every image is pinned and non-root (P10). Gate B still
refuses, because A isn't verified until you merge and approve. The run pauses:

```text
from run 20261113T180203Z
Task A draft PR: https://github.com/tosin2013/craz3-pilot-fixture/pull/3
Review and merge it on GitHub yourself, then run: pilot/pilot resume
```

If the run stops early, see [troubleshooting](troubleshooting.md#run-time).

---

## 9. The merge pause, then resume

Open the PR link. It's a **draft** opened by the publisher, and you are the reviewer. Check
that:
- it changes only these fixture files:

  ```text
  src/slugkit/slug.py
  src/slugkit/__init__.py
  tests/test_slug.py
  specs/001-slugify/tasks.md
  ```

- `slug.py` follows the spec: separator `~`, maximum 37 characters, an empty result gives
  `n~a`.

Click **Ready for review**, then **Merge**. Any merge method works.

Then:

```sh
pilot/pilot resume
```

**Prompt 3: approve the status change.** Reconcile checks that the PR really merged, that A's
tasks are complete, and that the merged files are exactly what was graded. Then it asks:

```text
from run 20261113T180203Z
Reconcile proposal for task A (item 001), PR #3 merged (393bc56…), tasks 100%, graded tree matches:
- ### 001 — Slug function  [status: planned]
+ ### 001 — Slug function  [status: verified]
Apply '001: planned → verified' to the fixture roadmap? [y/N]
```

Type `y`. The change is pushed to your fixture repo with your own GitHub login. Then gate B
allows B, B's worker runs (with the same live checks), B is graded, the publisher opens B's
draft PR, and the audit runs:

```text
from run 20261113T180203Z
  gate B: allow ['OK']
  ...
  PASS AU01 B refused (and never attempted) until A verified (SC-001)
  ...
  PASS AU11 induction applied to A/1 only, withholding exactly the acceptance section
run 20261113T180203Z succeeded.
```

- **If you run `resume` before merging,** it exits 4 and nothing changes. Merge first.
- **If you answer `N`,** it exits 5, the fixture roadmap is unchanged, and B stays blocked.

You can leave B's PR as a draft, or merge it; the pilot is complete either way.

---

## 10. Read the evidence and the audit

Each run writes an evidence folder. On a fresh clone that's
`pilot/runs/<run-id>/`, which is git-ignored and yours. (Maintainers working on a spec get
it in that spec's `evidence/` folder instead.)

- **`summary.md`:** start here. It shows elapsed time, the mode, every attempt and its
  grade, the PR links, and every event in order. From run `20261113T180203Z`:

  ```text
  | Task | Attempt | Induction                   | Grade             | Cost (USD) | Tokens |
  | A    | 1       | withheld-acceptance-section | fail (grade_fail) | 0.0        | 239363 |
  | A    | 2       | -                           | pass              | 0.0        | 477495 |
  | B    | 1       | -                           | pass              | 0.0        | 225354 |
  ```

  `Cost 0.0` means the provider reported no cost, so the token cap applied.

- **`audit.jsonl`:** the 11 audit checks, re-checkable later from the files alone.

  | Check | Meaning |
  |---|---|
  | AU01 | B was refused, and never attempted, until A was verified |
  | AU02 | The order was A/1 fail → A/2 pass → B pass |
  | AU03 | Exactly 2 draft PRs, both by the publisher's identity |
  | AU04 | No worker or grader held a repository credential |
  | AU05 | The gate's fail-closed self-checks passed |
  | AU06 | Every attempt stayed within its spend cap |
  | AU07 | Teardown was verified (after `pilot/pilot down`) |
  | AU08 | No secrets anywhere in the evidence |
  | AU09 | Every retry was confirmed by you |
  | AU10 | The mode was confirmed before any worker started |
  | AU11 | Only A/1 had its acceptance details withheld |

- **`checks/results.jsonl`:** the live isolation checks (P01–P10, GM01–GM04).
- **`attempts/<task>-<n>/`:** each attempt's prompt, report, change bundle and grade, and
  **`proxy-denials.log`**. Refusals there are expected; they show the allowlist working. In
  the reference run, the agent tried `bootstrap.pypa.io` (installing pip tools), and the
  pilot's own probe tried `github.com`. Both were blocked.
- **`config.json`:** your non-secret settings. The model host appears only as a hash.
- **`versions.txt`:** every tool and image version, with the Calico hash and image digests.

---

## 11. Tear down and confirm

```sh
pilot/pilot down
pilot/pilot audit
```

```text
from run 20261113T180203Z
  PASS T01 kind cluster deleted (absent)
  PASS T02 no kind node containers remain (containers=0)
  PASS T03 local registry container removed (containers=0)
```

`pilot/pilot audit` now passes all 11 checks, including AU07.

Optional cleanup:
- close or delete the PRs and the `pilot/<run-id>/<task>` branches on your fixture repo (or delete the repo);
- delete the fine-grained token on GitHub;
- remove `~/.config/specfoundry/` when you no longer need it.

---

## 12. When something goes wrong

Look up the message you see in [troubleshooting](troubleshooting.md). Each entry gives the
cause, the fix and how to confirm it.

If you're still stuck, open an issue at
[github.com/tosin2013/specfoundry/issues](https://github.com/tosin2013/specfoundry/issues)
with:
- the command you ran and its output;
- the output of `pilot/pilot status`;
- from the run's evidence folder: `run.json`, `events.jsonl`, and any failing attempt's
  `job.json` and `report.json`.

**Never share** anything from `~/.config/specfoundry/` or `~/.config/opencode/`, API keys,
tokens or your provider's hostname. The evidence files above contain none of these.

Report security problems privately, through GitHub's
[vulnerability reporting](https://github.com/tosin2013/specfoundry/security/advisories/new).

---

## 13. What will change

This guide describes the pilot today. Planned
[roadmap](../.specify/memory/roadmap.md) items will change some steps:

| Item | Effect on this guide |
|---|---|
| **004:** GitHub loop | PRs will come from a GitHub App (a bot identity) instead of your token, and issues will be created per task |
| **005:** OpenShift | An enterprise install path (restricted SCC, possibly images on Quay), and per-run model keys |
| **007:** Operator observability | Metrics, traces and events from each run to a collector you run |
| **008:** More harnesses | Claude Code and Codex workers alongside OpenCode |
| **macOS** | Needs multi-architecture images (amd64 and arm64); not yet scheduled |
