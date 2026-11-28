# Release notes

## A separate model for the test author (041, first part)

- `FORGE_AUTHOR_MODEL` (target profile, or `forge.env` for every target) sets the model that
  drafts hidden tests; workers keep `FORGE_MODEL`. Any model of the worker's provider, free or
  paid: for example a free worker and a paid author. Another provider is refused for now.
- `doctor` shows an `author model` row and checks the provider accepts the key for it.
- Each author Job and draft records its model, and the companion pull request names it
  ([targets: drafting hidden tests automatically](targets.md#drafting-hidden-tests-automatically)).

## Doctor reviews the target's CI (036, first part)

- `./chalkeus forge doctor --target <t>` now reads the target's CI whenever it has
  `.github/workflows/`, read-only: jobs red on the default branch (with the failed step, its
  command and the telling log line), CI's test commands next to the profile's (coverage,
  force-exit), the checks grading never runs (typecheck, lint, build, audit, commit lint), and
  CI's runtime versions against the toolchain. Warnings and information only
  ([targets: doctor's CI review](targets.md#doctors-ci-review)).
- Other Git hosts get one information line for now.

## Tracking issues readable by visitors

- A run's tracking issue now names the work instead of the run: `Chalkeus: <story> (<item> · <slice>)`.
  Its body links the item's spec and tasks, keeps a **Status** row up to date (waiting for a
  decision, draft PR ready, finished, back to planning), says visitors needn't do anything, and
  the run id moves to the footer. The issue gets a `chalkeus` label.
- Decision posts open with a plain question and fold the diagnosis into a collapsed section. The
  `/approve` commands and the hidden markers are unchanged.

Applies to runs started after the upgrade; open issues keep their text.

## Free models per target, and OpenCode 2.3.2

- The worker image runs **OpenCode 2.3.2**. Attempt reports now record the OpenCode version the
  worker actually ran (it said 2.2.7 whatever the image held).
- **`FORGE_ALLOW_FREE_MODELS=on`** in a target's profile lets that target's worker and test
  author use OpenCode's free models, which the image otherwise turns off. Off by default; the mode
  approval says when it's on ([targets](targets.md#2-configure-the-target)).

Nothing to do unless you want free models for a target.

## macOS: multi-platform images and Docker Desktop (031)

New:
- **Apple Silicon Macs are supported and validated**, with Docker Desktop: the fixture run and a
  target run (stockroom item 011, Java) passed with audit 11/11, and the isolation suite passed
  37/37. An Intel Mac is supported by design but not validated by the maintainer; arm64 Linux is
  untested. The operator guide has a macOS path ([section 4](operator-guide.md#install-on-a-mac)).
- **Multi-platform images:** every image in `pilot/images.lock` is now an index with
  `linux/amd64` and `linux/arm64`, each built natively on GitHub's runners. Docker pulls the
  build for your machine.
- **Per-architecture pins:** `pilot/pins.env` pins each upstream download once per architecture
  (`_AMD64` / `_ARM64` keys). The old single-architecture keys are removed; a build with a missing
  pin fails naming it.
- **spec-status 0.4.1**, the first release with builds for every host Chalkeus supports.
- **Doctor's host area:** `host`, `container runtime` and `spec-status` rows first, and after
  `up` the `node platform`, `image platforms` and `network token` rows. `up` refuses an
  unsupported host or a stopped Docker before installing anything.
- **`versions.txt`** records the host (`host_os`, `host_arch`, `runtime`), the node's and images'
  platform, and `host_spec`, the spec-status binary the gate actually ran.
- **Calico's network token:** on a Mac, Docker Desktop's VM pauses while the Mac sleeps and
  Calico can miss renewing its 24-hour token, after which no new pod starts. Forge now checks the
  token before each attempt and restarts `calico-node` when it won't last
  ([troubleshooting](troubleshooting.md#calico-token-expired)).
- **An App-only publisher** no longer needs a `publisher.env`: `up` requires the token file only
  for a token publisher, and `github-app.pem` for the App.

To do:
- **Pull `main`**, then run `./chalkeus forge up`: the lock's new image digests replace the old
  amd64-only ones.
- **Install spec-status 0.4.1** if your host has an older copy: the gate runs it, and `doctor`
  warns when it isn't the pinned release (operator guide section 4).
- **If you build images yourself or mirror them:** use the per-architecture keys in
  `pilot/pins.env`, and copy whole indexes, not one platform.

## Research before build: diagnosis, back to planning, doctor warnings (033)

New:
- **A diagnosis after every failed attempt**, shown with the retry question, on the tracking
  issue and in `summary.md` (`## Diagnosis`); kept as `attempts/<task>-<n>/diagnosis.json`. It
  lists what the evidence shows (research-worded tasks, files changed outside the allowed paths,
  egress refusals, an unrecognised failure, the test-run allowance) and recommends retry, raise
  the budget, or back to planning ([troubleshooting](troubleshooting.md#diagnosis)). It uses no
  model and never acts.
- **`replan`**, the other answer to a retry: `./chalkeus forge approve --run <id> replan` or
  `/approve replan` on the tracking issue ends the run as `stopped(back-to-planning)`. Step mode
  counts it as ended; the audit reports AU02 and AU03 as `n/a` for it.
- **Doctor warnings** for research-worded tasks, a runtime version the toolchain doesn't provide,
  and (with `--baseline`) how many full test runs fit in one attempt
  ([targets.md](targets.md#research-tasks)). Warnings never refuse a run.

- **Planning tools in the route back** (033 US5): a back-to-planning diagnosis names the Spec
  Kit Research Harness for unknown work and Bug Triage for a defect, with their commands when the
  target has them enabled and an install hint otherwise. A second timeout in a row with nothing
  else in the evidence now recommends back to planning instead of another retry.

The test-run time comes from the next tools image; until then doctor says it isn't recorded.
Nothing to do.

## Brownfield intake: dependency items (029, part 2)

New: a **dependency item** takes a dependency bump exactly as you approved it, and the agent fixes
the code around it ([targets.md](targets.md#a-dependency-upgrade-as-an-item)). Add a
`## Manifest change` section to the item's `spec.md` with the bump's commit (a bot PR's head
commit, for example) and its manifest files:
- `gate` and `doctor` check it (`manifest_change`): the commit is fetchable, it changes only the
  listed manifest files, and the files on the default branch still equal its parent. Forge never
  rebases a bot PR for you ([troubleshooting](troubleshooting.md#manifest-change)).
- The mode approval shows the commit, the files, and the packages and versions it changes.
- The baseline, the dependency cache and the worker start from the base with the bump applied;
  tests the bump breaks are the work.
- The manifest files are fixed: an attempt that changes them fails G2 with `MANIFEST_CHANGED`.
- The draft PR starts with the manifest commit (your files byte for byte, with
  `Chalkeus-Run: <run>`), then the agent's fixes.
- A dependency item is built whole: `--slice` is refused.

Also: [acting on the debt report](targets.md#acting-on-the-report), and the Spec Kit install
commands with an ADR folder check ([the planning tools](targets.md#the-planning-tools)).

The debt report reads private repositories' checks and each PR's advisories with the GitHub App's
**Checks**, **Commit statuses** and **Dependabot alerts** permissions, all read; it names any that
are missing. Nothing to do unless you want dependency items.

## Brownfield intake: the debt report (029, part 1)

New: `./chalkeus forge debt --target <name> [--json]`, a read-only report for an existing
repository ([targets.md](targets.md#an-existing-repository-the-debt-report)):
- its open Dependabot PRs, grouped by the checks they fail, with the checks shared by many PRs (or
  failing on the default branch) set apart, and each PR marked `superseded`, `safe`,
  `needs code changes`, `pending` or `not triaged`;
- baseline flags: a red default branch, test scripts that force an exit, packages with install
  scripts.

It writes nothing anywhere and runs nothing of the target's. With a GitHub App it mints a token
restricted to read permissions, in memory; otherwise it uses your read token. To read private
repositories' checks and the advisories each PR fixes, grant the App **Checks**, **Commit
statuses** and **Dependabot alerts** (all read). Nothing else to do.

## Chalkeus: forge's own output (027, stage 5)

Forge's messages, help and GitHub text now use the new names too:

| Before | Now |
|---|---|
| messages that name a setting, for example `not in PILOT_APPROVERS` | `FORGE_*`, for example `not in FORGE_APPROVERS` (the `PILOT_SCM_*` publisher keys keep their names) |
| `… in pilot.env` | `… in forge.env` |
| PR and issue text "Opened by the specfoundry … publisher", "Generated from the roadmap by specfoundry" | Chalkeus |
| hidden issue markers `<!-- specfoundry:item=…` and `<!-- specfoundry:decision …` | `<!-- chalkeus:… -->` |
| commit trailer `Specfoundry-Run: <run id>` | `Chalkeus-Run: <run id>` |

Nothing to do. Forge still reads the old markers: an issue synced before is matched to its item,
and its next sync rewrites the body with the new marker; a run paused before the update finds the
decision it already posted instead of posting it again. Commits made before keep their old
trailer. Scripts that matched the old message text need the new names.

## Chalkeus: the cluster, labels and images (027, stage 4)

| Before | Now |
|---|---|
| kind cluster `specfoundry-m1` (context `kind-specfoundry-m1`) | `chalkeus-m1` (`kind-chalkeus-m1`) |
| local registry container `specfoundry-registry` | `chalkeus-registry` (still on port 5001) |
| Kubernetes labels `specfoundry.io/role`, `specfoundry.io/run`, `specfoundry.io/draft` | `chalkeus.io/…` |
| images `ghcr.io/tosin2013/specfoundry-pilot-*` | `ghcr.io/tosin2013/chalkeus-*` |

Runs and evidence from before are unchanged: the audit never read the labels, and old images
stay published.

### Each operator's steps

1. **Finish or stop any run in progress first.** A paused run lives in the old cluster.
2. **Take the old cluster down** with the command from before the update, or by hand:

   ```sh
   kind delete cluster --name specfoundry-m1 && docker rm -f specfoundry-registry
   ```

   If you skip this, `./chalkeus forge up` refuses and prints that command, and
   `./chalkeus forge doctor` warns about it. Chalkeus never removes it for you.
3. **`git pull`, then `./chalkeus forge up`.** It creates `chalkeus-m1`.

### The images

The image workflow publishes `chalkeus-*` when this change reaches `main`, then opens its usual
digest PR for `pilot/images.lock`. Until that PR is merged, `up` pulls the old
`specfoundry-pilot-*` digests from the lock, which stay published. The owner checks once that
the new packages are public (GitHub → Packages → each `chalkeus-*` → Package settings), since
`up` pulls them without credentials.


## Chalkeus: the rename (027, stage 3)

specfoundry is now **Chalkeus**, and its pilot is **forge**. The in-repository command is
`./chalkeus forge <cmd>`. `pilot/pilot` is removed: it's a hard switch, with no alias. Every
command, flag and exit code is the same; only the name in front changes.

| Before | Now |
|---|---|
| `pilot/pilot run`, `pilot/pilot approve …` | `./chalkeus forge run`, `./chalkeus forge approve …` |
| `pilot/pilot version` | `./chalkeus version` (or `./chalkeus forge version`) |
| `~/.config/specfoundry/` | `~/.config/chalkeus/` (the old folder is still read) |
| `pilot.env` | `forge.env` (the old name is still read) |
| `PILOT_*` settings, for example `PILOT_MODEL` | `FORGE_*`, for example `FORGE_MODEL` (the old names are still read) |
| `SPECFOUNDRY_CONFIG` | `CHALKEUS_CONFIG` (the old name is still read) |
| step mode's default label `pilot/go` | `chalkeus:proposed` |
| the `pilot` agent skill | the `forge` skill (`.claude/skills/forge/`) |
| github.com/tosin2013/specfoundry | github.com/tosin2013/chalkeus (GitHub redirects the old address) |

The kind cluster, the local registry, the image names and the Kubernetes labels moved in
stage 4 ([below](#chalkeus-the-cluster-labels-and-images-027-stage-4)).

Every old name that still works prints a one-time notice with its new name. When you set both
an old and a new name, the new one wins and the notice says which one is ignored. The full map is
[contracts/name-map.md](../specs/027-chalkeus-rename/contracts/name-map.md).

### The owner's steps, on the day

1. Merge the stage 3 pull request.
2. The same day, rename the repository: GitHub → Settings → General → Repository name →
   `chalkeus`. GitHub redirects the old address for clones, pulls and links.
3. Never create a new repository named `specfoundry` under the same account: it would replace
   the redirect.
4. Check that the go, integration and image workflows pass on the renamed repository.

### Each operator's steps

1. **Update your checkout.** `git pull`. Optionally point it at the new address (the old one
   redirects):

   ```sh
   git remote set-url origin https://github.com/tosin2013/chalkeus.git
   ```

2. **Use the new command.** `./chalkeus forge doctor` builds it on first use. Scripts and notes
   that call `pilot/pilot` must change; it no longer exists.
3. **Update your own harness rules.** This repository's `.claude/settings.json` already asks before
   the ten commands that decide, destroy or hold credentials, in the new form. If you added rules
   to your own harness config (for example OpenCode's `~/.config/opencode/opencode.json`), replace
   each `pilot/pilot <cmd>` pair with `./chalkeus forge <cmd>` and `chalkeus forge <cmd>`
   ([prompts answer "no"](troubleshooting.md#prompts-answer-no) lists the ten).
4. **Restart your coding agent's session** in this repository, so it loads the `forge` skill and
   the new rules.
5. **Move the config folder (optional, recommended).** Until you do, Chalkeus reads the old one
   and says so once. Keep its permissions with `mv`:

   ```sh
   mv ~/.config/specfoundry ~/.config/chalkeus
   ```

   Chalkeus never moves, copies or writes into either folder itself.
6. **Rename your settings (optional).** In `forge.env` (or `pilot.env`) and in each
   `targets/<name>.env`, `FORGE_X` replaces `PILOT_X` with the same suffix. Keep the publisher
   credential files (`publisher.env`, `targets/<name>.publisher.env`) as they are: their keys
   don't change.
7. **Step mode's label.** If a target profile sets no `FORGE_PROPOSE_LABEL` (or
   `PILOT_PROPOSE_LABEL`), step mode now looks for the label `chalkeus:proposed`. Either relabel
   the issues you proposed with `pilot/go`, or keep the old label in the profile:

   ```sh
   FORGE_PROPOSE_LABEL=pilot/go
   ```

   `./chalkeus forge step` says when open issues still carry `pilot/go` while the profile relies
   on the default.

Runs, evidence and audits from before the rename are unchanged: an old run resumes and audits as
before with the new command.
