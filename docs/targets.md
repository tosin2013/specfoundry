# Your own repositories (targets)

The fixture shows the pilot's guarantees on two built-in items. A **target** is one of your own
repositories. You prepare its items with Spec Kit; the pilot then runs only items that are
prepared, under the same guarantees. This page covers configuring targets, checking whether an item
is ready, and running it (roadmap item 014). The toolchains are `python3.13`, `node24`, `go` and
`jdk21-maven`, plus the built-in `python` (Python 3.11 with pytest) for a project whose tests need
no packages; any other language needs [your own toolchain image](#your-own-toolchain-image).

Starting from an empty repository? Plan it first, then build it item by item:
[greenfield.md](greenfield.md). An existing repository with a pile of bot PRs or red CI? Start
with [the debt report](#an-existing-repository-the-debt-report).

## An existing repository: the debt report

Before you prepare the first item of an existing repository, look at what it carries:

```sh
./chalkeus forge debt --target <name>          # add --json for the data
```

The report is read-only: it never comments, labels, merges, closes or re-runs anything, and it runs
nothing of the target's. It needs no cluster and no model.

- **Open Dependabot PRs, grouped by the checks they fail.** A check is **shared** when it also
  fails on the default branch, or when it doesn't run there but fails on most of the PRs (an
  auto-merge job blocked by a red required check, for example). A shared check says nothing about
  one PR: fix it once, and the group unblocks.
- **Each PR's class:**
  - `superseded`: the default branch's lockfile already has that version or newer, or a newer bot
    PR bumps the same package. Close it;
  - `safe`: a patch or minor bump that fails no check of its own;
  - `needs code changes`: a major bump, or a check of its own fails. Forge can build the code
    change as a [dependency item](#a-dependency-upgrade-as-an-item);
  - `pending`: its checks haven't finished;
  - `not triaged`: another bot, an ecosystem without a toolchain, or checks the credential can't
    read.
- **Baseline flags:** a red default branch (a forge baseline on it fails too), test scripts that
  force an exit (`--forceExit`, Mocha `--exit`), and packages with install scripts
  ([native builds](#installs-that-build-native-code-or-download-files)).

You decide what to merge, batch or close. What the report couldn't read shows as `unknown`, never
as `safe`.

**Credentials.** With a GitHub App (`FORGE_PUBLISHER_CREDENTIAL=app`), the report mints its own
token for that one repository with read permissions only, kept in memory. Otherwise it uses your
read token (`GH_TOKEN`, `GITHUB_TOKEN`, then `gh auth token`). It never uses the publisher's
token. For private repositories, and for advisories, grant the App **Checks**, **Commit statuses**
and **Dependabot alerts**, all read; the report names whichever is missing.

### Acting on the report

Forge proposes; you act on GitHub yourself:

1. **Fix the shared checks first.** A check that fails on the default branch, or on most bot PRs,
   is one problem, not twenty. Fix it on the default branch (by hand or as an ordinary item),
   then let the bot rebase its PRs.
2. **Close the `superseded` PRs**, and merge or batch the `safe` ones as you normally would.
3. **Fix the baseline flags** before the first run:
   - a **red default branch**: a forge baseline on it fails too, so fix it first;
   - **test scripts that force an exit**: the flag hides tests that leave handles open. Keep it in
     `FORGE_TEST_COMMAND` for now if you must, and plan an item that fixes the leaks;
   - **install scripts**: see [native builds](#installs-that-build-native-code-or-download-files)
     (`npm ci --ignore-scripts` when the native build isn't needed).
4. **Turn each `needs code changes` PR you want into a dependency item** (next section), or close
   it.

### A dependency upgrade as an item

A major bump (zod 3 → 4, for example) breaks code. A **dependency item** takes the bump exactly as
you approved it, and the agent fixes the code around it. Prepare it like any item
([section 1](#1-prepare-the-repository)), plus:

1. **Get the bump onto the current default branch.** The listed files at the base must equal the
   commit's parent. If the bot PR is behind, ask the bot to rebase it (`@dependabot rebase`), or
   commit the same change yourself on a branch from the current default branch and push it.
   Forge never rebases anything.
2. **Name the commit in the item's `spec.md`**, beside `## Allowed paths`:

   ```markdown
   ## Manifest change

   - Commit: `3f9c2d0e8b7a6c5d4e3f2a1b0c9d8e7f6a5b4c3d`
   - Files: `package.json`, `package-lock.json`
   ```

   Exactly one full 40-character commit, and every file its diff changes (no globs). The files
   must be the toolchain's dependency manifests. Other lines are ignored, so you can note which
   bot PR it came from. The commit must be fetchable from the target: a bot PR's head commit is.
3. **Write the tasks as the code change** ("move the schemas to zod 4's API"), with allowed paths
   for the code. The manifest files need not be listed: the agent may not change them.
4. **Write hidden tests that guard what must not change**: the behaviour your users rely on, which
   the upgrade must keep. Visible tests the bump breaks are already part of the work.

What the run does:
- `gate` and `doctor` check the section (`manifest_change`); each problem refuses the item with a
  `MANIFEST_CHANGE_…` code ([troubleshooting](troubleshooting.md#manifest-change)).
- The mode approval shows the commit, the files, and the packages and versions it changes.
- The baseline, the dependency cache and the worker all start from the base with the bump applied.
  Visible tests the bump breaks are recorded in the baseline; afterwards they must pass, with the
  hidden tests. If the bump breaks no visible test, the hidden tests must fail on it instead.
- An attempt that edits, deletes or renames a manifest file fails G2 with
  `MANIFEST_CHANGED: <file>`.
- The draft PR starts with the manifest commit (your approved files byte for byte, with the
  commit's author and subject and `Chalkeus-Run: <run>` in its body), then the agent's fixes.
- A dependency item is built whole: `--slice` is refused.

After you merge forge's PR, close the bot PR if the bot hasn't already.

## 1. Prepare the repository

For each item you want the pilot to build:

- **The roadmap** (`.specify/memory/roadmap.md`) lists the item. Every dependency is
  `verified`, and the item's `Spec dir` points to its folder.
- **The item's folder** has `spec.md` and `tasks.md`. The spec has no `[NEEDS CLARIFICATION`
  markers left, and no open question in the roadmap names the item.
- **The spec says what the agent may change**, in an `## Allowed paths` section. Each list
  item's first backticked text is one glob:

  ```markdown
  ## Allowed paths

  - `src/main/java/com/example/*`
  - `src/test/java/com/example/*`
  ```

  `*` also matches `/`, so the first line covers everything under that folder. The item's
  `tasks.md` is always allowed, so the agent can tick its tasks. A glob that could reach
  `.github/`, `.specify/`, the roadmap or another item's spec folder is refused.
- **Hidden acceptance tests** live in a separate **private** repository: the *companion*. They
  go in `items/<NNN>/`, laid out like the project (for example `items/002/src/test/java/…`).
  - **One companion can serve all your targets**, in any languages. Give each target its own
    folder and name it with `FORGE_COMPANION_PATH` (section 2):

    ```text
    my-acceptance/                                  (private)
    ├── cli-schema-mcp/items/006/tests/test_bundled_flags.py
    ├── helmdeck/items/002/internal/server/router_test.go
    └── greeting-service/items/002/src/test/java/…/GreetingTest.java
    ```

    The companion is only storage: nothing builds it as a whole. For a run, the pilot copies
    just that item's folder over a clean copy of the project, and the project's own test
    command compiles and runs it. Your editor won't resolve the tests' imports while you browse
    the companion on its own; that's expected.
  - Give access to the companion only to the people who write hidden tests, and never open it
    in the coding agent that runs the pilot: an agent that sees the tests can write code that
    passes them without doing what the spec asks. A separate test-author session may draft them
    for you (see "Drafting hidden tests with the test author" below).
  - The pilot reads them on your machine with your own git access, and gives them only to the
    grader. The agent never sees them.
  - They must fail on the current code.
  - They may only use dependencies the project's build already declares.

### The planning tools

Prepare items with Spec Kit and two extensions, the roadmap and spec-status. With Spec Kit 1.4.3,
from the repository root:

```sh
pipx install uv
S="uvx --from git+https://github.com/github/spec-kit.git@v1.4.3 specify"
$S init --here --integration claude --script sh --ignore-agent-tools --force --non-interactive
$S extension add roadmap --from https://github.com/srobroek/speckit-roadmap/archive/refs/tags/v0.1.1.zip
$S extension add spec-status --from https://github.com/tosin2013/spec-status/releases/download/v0.4.0/spec-status-extension_0.4.0.zip
```

- `--integration` names your coding agent (it was `--ai` before Spec Kit 1.4). Both extensions
  are community extensions, not vetted by Spec Kit: `extension add` asks you to trust each.
- **Where are your ADRs?** The roadmap extension looks in your repository's docs/adr folder. If
  yours are elsewhere (docs/adrs, for example), set `adr.dir` in `.specify/extensions/roadmap/roadmap-config.yml`,
  then check it took effect: `.specify/extensions/roadmap/scripts/bash/load-config.sh` prints
  `adr_dir` and `adr_present`.
- **If that check ignores your settings** (it reports the extension's own roadmap, or the default
  `adr_dir`), the installed archive carried a nested `.specify/` folder and the script took the
  extension's folder for the repository root. Until a fixed release, set `SPECKIT_ROADMAP_PATH`
  and `SPECKIT_ROADMAP_ADR_DIR` in your environment.
- **Agent skills are per machine** unless you commit them: `specify init` writes your agent's
  skills (`.claude/skills/` for Claude Code), and many repositories ignore that folder. Commit
  them, or run `init` on each machine you plan from.

<a id="research-tasks"></a>
### Research tasks and environment changes belong in planning

An attempt builds known changes. Two kinds of work can't be done inside one, however much time
it gets, so resolve them while you plan the item, before its tasks:

- **Research:** a task whose answer isn't known when you write it. A task that starts with one of
  these phrases reads as research: `locate`, `find out`, `find the`, `find which`,
  `investigate`, `identify the cause`, `identify which`, `figure out`, `determine why`,
  `determine which`, `diagnose`, `research`, `explore`, `spike`. Do the investigation yourself
  (or with an agent that assists you), record the answer in the item's `research.md` with
  `/speckit-plan`, and regenerate the tasks with `/speckit-tasks`, so each one names the change
  to make. The Spec Kit Research Harness extension (`harness`, community, not vetted by Spec Kit)
  runs such an investigation within a budget and writes the findings into `research.md`; the core
  Bug Triage extension (`specify extension add bug`) suits a defect such as a flaky test.
- **Environment changes:** the runtime or toolchain, dependencies and the lock file, native
  install scripts, registries and other egress hosts, or the pod budget. An attempt can't change
  them: make them in your planning PR (dependencies, version files, CI) or in the target profile
  (`FORGE_REGISTRY_HOSTS`, `FORGE_WORKER_DEADLINE_S`).

`./chalkeus forge doctor --target <t> --item NNN [--slice <id>]` warns about research-worded
tasks and about a runtime version the toolchain doesn't provide. With `--baseline` it also times
one run of the project's test command and warns when fewer than 5 full runs fit in one attempt
under the worker deadline. These are warnings: they never refuse a run.

If an attempt fails anyway, the retry question shows a diagnosis with a recommendation (retry,
raise the budget, or back to planning); to go back to planning, end the run with
`./chalkeus forge approve --run <id> replan` and start a new run after the planning change is
merged (see [troubleshooting: diagnosis](troubleshooting.md#diagnosis)).

Example (an existing repository): documcp's first Node 24 slice had a task "Locate the suites
that leave handles open". The attempt spent its whole 40-minute deadline searching, and changed
`package-lock.json`, which wasn't an allowed path. A per-folder scan outside the run found the
two leaks and the one test that wrote into the repository in about 20 minutes; with that in
`research.md`, the tasks became three named fixes.

## 2. Configure the target

Target settings live on your machine, never in the target repository. They go in a `targets`
folder next to `forge.env`:

```text
~/.config/chalkeus/              # or $CHALKEUS_CONFIG, if you set it
├── forge.env                       # shared: model, approvers, publisher mode
├── publisher.env                   # token mode only: the fixture's token
└── targets/                        # you create this folder; the pilot doesn't
    ├── greeting.env                # the profile for `--target greeting`
    └── greeting.publisher.env      # optional: this target's own token (section 4)
```

- **The file name is the target's name.** `--target greeting` reads `targets/greeting.env`.
  A name is lower-case letters, digits and `-`.
- **Create the folder and the file yourself, readable only by you.** For example, on a machine
  where your home is `/home/ubuntu`, the full path is
  `/home/ubuntu/.config/chalkeus/targets/greeting.env`:

```sh
install -d -m 0700 ~/.config/chalkeus/targets
install -m 600 /dev/null ~/.config/chalkeus/targets/greeting.env
$EDITOR ~/.config/chalkeus/targets/greeting.env
```

- **The pilot checks the modes:** the folder must be `0700` and each file `0600`, otherwise it
  stops with `TARGET_MODE`. If you made them with `mkdir` or an editor, run
  `chmod 700 ~/.config/chalkeus/targets` and `chmod 600 ~/.config/chalkeus/targets/*.env`.
- **Check your profiles** with `./chalkeus forge targets`: it lists each one, or says why it's invalid.
- **If the file is missing**, the pilot stops with `TARGET_UNKNOWN: no target "greeting":
  create …/targets/greeting.env`, and prints the full path it looked for.

The profile's contents:

```sh
FORGE_TARGET_REPO=you/greeting-service
FORGE_TARGET_BRANCH=main
FORGE_TOOLCHAIN=jdk21-maven
FORGE_TEST_COMMAND=mvn -B test
FORGE_REGISTRY_HOSTS=repo.maven.apache.org
FORGE_COMPANION_REPO=you/my-acceptance
FORGE_COMPANION_PATH=greeting-service       # optional: this target's folder in a shared companion
FORGE_GITHUB_ISSUES=off
```

- **Your repository declares none of this.** No agent change or merged PR can widen what the
  worker may reach.
- **`FORGE_TOOLCHAIN`** names a toolchain Chalkeus builds: `jdk21-maven`, `node24`,
  `python3.13` or `go` (`pilot/images/toolchains.json`). Until its image is published, the pilot
  refuses with `TOOLCHAIN_UNAVAILABLE`.
- **Dependencies:** list the package registries in `FORGE_REGISTRY_HOSTS` and set
  `FORGE_INSTALL_COMMAND`. The install runs twice: once for the agent (with the registries
  reachable), and once, before any attempt, into a cache built from your unchanged code plus the
  hidden tests. The grader then runs offline from that cache, so **an attempt can't add
  dependencies**; add new ones to the project yourself when you prepare the item. The same goes
  for a runtime upgrade: an item that moves the project to a new Node, Python or Java version can
  only declare the version and fix code, so the matching type packages (`@types/node`), lock file
  and CI version go in your own planning PR first. The registries
  are shown when you approve the mode, and check P06r confirms each attempt's network: a declared
  registry is reachable, any other host (`example.invalid`) is refused, and the install's proxy
  allows only the registries. What the agent tried and was refused is in the attempt's
  `proxy-denials.log`. For Python
  (`python3.13`):

  ```sh
  FORGE_TOOLCHAIN=python3.13
  FORGE_REGISTRY_HOSTS=pypi.org,files.pythonhosted.org
  FORGE_INSTALL_COMMAND=pip install -r requirements.txt      # dependencies only, not -e .
  FORGE_TEST_COMMAND=PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests
  ```

  The packages go into a virtual environment the pilot creates; your tests must find the project's
  own code through `PYTHONPATH` or your pytest configuration.

  The other catalog toolchains, as tested offline in `pilot/images/toolchain-samples/`:

  | `FORGE_TOOLCHAIN` | `FORGE_REGISTRY_HOSTS` | `FORGE_INSTALL_COMMAND` | `FORGE_TEST_COMMAND` |
  |---|---|---|---|
  | `node24` | `registry.npmjs.org` | `npm ci` | `npm ci --offline && npm test` |
  | `go` | `proxy.golang.org,sum.golang.org` | `go mod download` | `go test ./...` |
  | `jdk21-maven` | `repo.maven.apache.org` | `pilot-maven-prefetch` | `mvn test` |

  - **Node:** packages are cached in the dependency cache (`npm_config_cache`), and `npm ci
    --offline` rebuilds `node_modules` from it in the grader. Commit your `package-lock.json`.
  - **Go:** the module cache is the dependency cache; `GOTOOLCHAIN=local`, so a `toolchain` line
    newer than the image's Go fails instead of downloading another Go.
  - **Maven:** the pilot sets `MAVEN_ARGS` for each role: a generated `settings.xml` pointing at
    the target's proxy while installing, and `-o` with the cache chained read-only
    (`maven.repo.local.tail`) in the grader. Use `pilot-maven-prefetch` (part of the toolchain)
    as the install command. Maven downloads its test-runner plugin only when tests actually run,
    so the helper runs your tests, with the hidden ones included and failures ignored. When the
    hidden tests don't compile yet (they use classes the item will add, which is normal for a new
    project), it runs the test phase again with one trivial test in their place. Only your
    `pom.xml` decides what is downloaded.
- **Any other language:** bring your own toolchain image (next section), or ask for one with the
  [toolchain image request form](https://github.com/tosin2013/chalkeus/issues/new?template=toolchain-image.yml).
- **If the project requires tests with every change**, set `FORGE_TEST_PATHS` to its test files
  (for example `tests/*` or `src/test/*`). The grader then adds two checks:
  - **G6:** the change must add or edit at least one test file. A change without tests fails,
    and the agent is told to add them.
  - **G7:** the change can't pass by weakening a test. The grader puts back the original version
    of every existing test file the change edited or deleted and runs your tests again; they
    must still pass. If an item is meant to change what an existing test expects, list that
    file in the spec under `## Tests that may change`.

  The test paths must also be in the item's `## Allowed paths`, or the agent can't add tests.
  The project's other gates (coverage, linters) can go in `FORGE_TEST_COMMAND` if they pass on
  your current code; the baseline check confirms that before any attempt. Either way, your
  repository's own CI runs on the PR.
- **PR titles follow [Conventional Commits](https://www.conventionalcommits.org/)**, because many
  projects squash-merge and use the PR title as the changelog entry. The item's PR is
  `feat(<item>): <the item's roadmap title>`; set `FORGE_CHANGE_TYPE` (`fix`, `refactor`, `perf`,
  `test`, `docs`, `build`, `ci`, `style` or `chore`) when the item isn't a feature. The
  status-change PR and its commit are `docs(roadmap): <item> verified`. The item's commit
  carries the same title as its PR, because GitHub squash-merges a one-commit PR with the
  commit's message; the worker's message and a `Chalkeus-Run: <run id>` trailer follow. The
  run id is also in each PR's branch name and body.
- **Authorship and sign-off.** The pilot's commits are authored by its publisher identity (your
  GitHub App or token), which is the truth: you didn't write the code. The pilot never adds
  `Signed-off-by` or `Co-authored-by` for you, because a sign-off is your own statement. If your
  project wants a human sign-off on every change (for example a DCO policy), turn on **Settings →
  General → Require contributors to sign off on web-based commits** in the target repository:
  when you squash-merge a pilot PR in the web interface, GitHub adds **your** `Signed-off-by`.
- **Optional keys** may only raise the toolchain's defaults: `FORGE_GRADER_MEMORY`,
  `FORGE_GRADER_DEADLINE_S` and `FORGE_CACHE_SIZE`; for the agent's pod, `FORGE_WORKER_CPU`
  (default `2`), `FORGE_WORKER_MEMORY` (default `2Gi`) and `FORGE_WORKER_DEADLINE_S` (seconds
  per attempt, default 1200); for the test author's Job, `FORGE_AUTHOR_DEADLINE_S` (seconds per
  author Job, default 1200). `FORGE_MAX_INPUT_MB` (default 50) limits the repository snapshot.
  A run keeps the budget it started with; delete a line to go back to the default for the next
  run. The worker stops the agent 2 minutes before its deadline, so an attempt that runs out of
  time still keeps its change, log, tokens and cost as evidence (it isn't graded), and the
  retry question says how far it got.
- **Free models are off unless the target opts in.** The worker image turns off OpenCode's free
  models (`OPENCODE_DISABLE_FREE_MODELS`), so a free model such as `opencode-go/beam-free` fails at
  once with `provider.no-route` ("Model unavailable"). Set `FORGE_ALLOW_FREE_MODELS=on` in a
  target's profile to let that target's worker and test author use them. The mode approval says
  so, and a run keeps the setting it started with. Free models may handle requests differently
  from paid ones, and some train on request data (OpenCode then asks your organisation to allow
  it), so decide per target.
- **The target repository can't be this one or any target's companion.** The pilot refuses
  with `TARGET_IS_CANARY`.

### Installs that build native code or download files

The sandbox reaches only the registries in `FORGE_REGISTRY_HOSTS`, and the grader reaches
nothing. An install step that downloads from anywhere else, or compiles native code with tools
the toolchain doesn't have, fails before any attempt, in the dependency prefetch:

```text
PREFETCH_FAILED … (the log tail shows the blocked download or the missing compiler)
```

The full log tail is in the run's (or the draft's) `prefetch.json`. Check first whether the
project needs the native part at all; often a prebuilt or WebAssembly version is already used.

| Toolchain | Usual cause | What to do |
|---|---|---|
| `node24` | A package's install script runs `node-gyp rebuild` (`sqlite3`, `bcrypt`, `tree-sitter-*` grammars), which downloads Node's headers from nodejs.org and needs a C++ compiler | If the tests pass without it, add `--ignore-scripts` to both commands: `npm ci --ignore-scripts` and `npm ci --offline --ignore-scripts && npm test`. Run the full suite that way on your machine first |
| `python3.13` | A package has no wheel for the image's Python and platform, so pip builds the source distribution | Pin a version that publishes a wheel (`pip download --only-binary=:all: <pkg>` tells you), or drop the dependency |
| `go` | cgo packages need a C compiler; `go generate` steps that fetch tools | Build with `CGO_ENABLED=0` in `FORGE_TEST_COMMAND` if the project allows it; commit generated files |
| `jdk21-maven` | A plugin downloads a binary during the build (for example a Node or protoc download) | Skip it in tests with a Maven profile or property, or bind it to a phase the tests don't run |

If the project really needs the native build, or a language or version Chalkeus doesn't ship,
use [your own toolchain image](#your-own-toolchain-image) with the compiler and headers in it, or
ask for one with the
[toolchain image request form](https://github.com/tosin2013/chalkeus/issues/new?template=toolchain-image.yml).

### Your own toolchain image

A toolchain image only supplies a language's tools. It holds `/opt/toolchain/` with a
`toolchain.json` describing them. The pilot copies them into the agent's and the grader's
pods; the agent's sandbox and the grader stay Chalkeus's own images. The format is in
[the toolchain image contract](../specs/014-any-project/contracts/toolchain-image.md). A
template is coming: a UBI Dockerfile for Red Hat and OpenShift, a Debian one for elsewhere, and
a GitHub Actions workflow that builds and attests the image.

```sh
FORGE_TOOLCHAIN=rust-1.83
FORGE_TOOLCHAIN_IMAGE=quay.io/you/toolchain-rust@sha256:<64 hex>
```

- The image must be pinned by digest; a tag is refused.
- Its name can't be one of Chalkeus's toolchains.
- The mode approval shows it as operator-supplied, and the run's evidence records it so.
- It runs your project's tests inside the grader, so keep it trustworthy, as you would any base
  image.

List what's configured:

```sh
./chalkeus forge targets
```

It prints each target's repository, toolchain, registries and companion, or why the target is
invalid. It never prints a secret or your model host. `fixture` is always listed; it is the
repository in `forge.env`.

`./chalkeus forge reset-fixture` only ever acts on the fixture. With `--target` naming any other
target it refuses with `NOT_A_FIXTURE`, because it force-pushes.

### AI-driven apps

Chalkeus builds AI-driven apps like any other: the worker codes with its own model, and the
grader checks the change with your deterministic tests, offline. Write hidden tests for the code
around the model (how prompts are built, how tools are wired, how structured output is parsed,
retries and guardrails) with a **fake model** or recorded responses; Spring AI, LangChain4j and
most SDKs let tests swap one in.

Judging what a live model actually does ("is the answer good?", "does retrieval find the right
document?") is **evaluation**, not grading: it is probabilistic and depends on the model version.
That belongs to your own evaluation tools and CI, which you can read before you merge the PR.
Chalkeus doesn't run live-model evaluations, and its graders have no model access (roadmap
C-16).

### Hidden tests: who can see what, and why

A build worker sees only the item's spec and tasks and a snapshot of the target repository, and
it has no route to GitHub. The one realistic way it could learn the hidden tests is if they
**land in the target repository**: an agent copies them there by mistake or because a file
tricked it (a prompt injection), or a bug carries them over. The next run's snapshot would then
contain them. The pilot refuses such a run (`HIDDEN_TESTS_IN_TARGET`), and the **security level**
in the target's profile decides who may write the target and read the companion:

| `FORGE_SECURITY_LEVEL` | For | The test author's identity | What keeps tests out of the target |
|---|---|---|---|
| `minimal` (default) | one developer on a laptop | your own git access | branch protection on the target, your review of every PR, the skill's rules, the `HIDDEN_TESTS_IN_TARGET` check |
| `recommended` | teams | a token that can write **only** the companion, in `targets/<name>.author.env` as `FORGE_AUTHOR_TOKEN` (mode 0600) | GitHub itself: that identity can't write the target |
| `strict` | enterprise, cluster mode | a separate GitHub App, companion only, in its own Job | as recommended, plus enforced network limits (arrives with cluster mode) |

Build-worker isolation is the same at every level. Separate identities are recommended for
teams and expected in enterprise environments, where review alone doesn't scale and who wrote
the tests versus who wrote the code must be clear. Each run records its level, and the audit
reports it. At the minimal level, **protect the target's main branch** so changes arrive only by
reviewed pull request.

### Drafting hidden tests with the test author

Instead of writing an item's hidden tests yourself, you can have a **separate** agent session
draft them. Open a new session (not the one that runs the pilot), load the test-author skill
(`.claude/skills/test-author/`), and give it the target and item. It runs:

```sh
./chalkeus forge author start --target greeting --item 002    # checks the item; prints a workspace
./chalkeus forge author check --target greeting --item 002    # on the cluster: your tests pass, the drafted tests fail
./chalkeus forge author submit --target greeting --item 002   # opens a pull request on the companion
./chalkeus forge author status --target greeting --item 002   # where the draft stands
```

- The pull request touches only the item's folder in the companion and includes a coverage
  table: which acceptance criteria of the spec each test covers, and which are uncovered.
- **You review and merge it.** Merging is the approval; the pilot never merges.
- The draft's evidence records names, hashes and results, never the tests' contents.
- The test author never runs `run`, `resume` or `approve`, and never writes the target.

### Drafting hidden tests automatically

With auto-draft on, you don't start the test author yourself. A watcher notices when an item is
ready except for its hidden tests (you merged its spec and tasks, and the companion has no tests
and no open draft for it), drafts them, and opens the same companion pull request. You still
review and merge it, and you still approve every run.

1. In the target's profile, set `FORGE_AUTHOR_AUTO=on`. Optional: `FORGE_AUTHOR_INTERVAL_S`
   (seconds between checks, default 120) and `FORGE_AUTHOR_AUTO_ATTEMPTS` (author Jobs per
   draft, default 2).
2. Run `./chalkeus forge up`. It creates the author's proxy, which lets it reach only your model.
3. In **your own terminal**, start the watcher:

   ```sh
   ./chalkeus forge author watch --target greeting           # Ctrl-C stops it
   ./chalkeus forge author watch --target greeting --once    # one check, then exit
   ```

It prints one line per decision: `skip NNN: <why>`, `draft NNN: started …`, then
`DRAFT_OK, opened <url>`, or `attempt <n> <code>` for each failed attempt and then
`failed, no PR`. It runs at `-vv` by default, printing the author Job's
pod phases and events, checks A01-A05, its spend, and anything the author's proxy refused, on
stderr. Pass `-v` for less, or set `FORGE_VERBOSE=0` to turn it off. The agent's live activity
(`-vvv` for build workers) is never shown for the author, because it would print the drafted
tests.

- **The author runs sandboxed:** a Job in its own namespace on your cluster, using the same
  OpenCode as the workers, and their model unless you choose another (below). It can reach only the model, holds no GitHub credential,
  and shares nothing with build workers. Checks A01-A05, in the draft's evidence, prove it for
  every Job.
- **The pilot, not the Job, checks the draft** (your tests pass, the drafted tests fail on
  today's code) and opens the pull request with your target's usual test-author identity.
- **A draft that runs out of time** (`DeadlineExceeded`, no draft) needs a longer author Job:
  raise `FORGE_AUTHOR_DEADLINE_S` in the target's profile (documcp's skill slice needed more than
  the default 20 minutes), then start the watcher with `--redraft`.
- **A failed check gets one more try:** a second Job sees the failure. After that, the item
  waits until its spec changes, or you draft by hand. An item is never drafted twice for the
  same spec, unless you start the watcher with `--redraft`
  (`./chalkeus forge author watch --target <name> --redraft`): it drafts each waiting item or
  slice once more, for example after a forge fix.
- **A stronger model for the test author (041):** a hidden test is drafted once and grades
  every attempt, so a mistake there costs the most. Set `FORGE_AUTHOR_MODEL` in the target's
  profile (or in `forge.env` for every target) to draft with another model of the worker's
  provider, free or paid; the workers keep `FORGE_MODEL`. For example, workers on
  `opencode-go/beam-free` and the author on `opencode-go/deepseek-v4-pro`. A paid model needs no
  opt-in; `FORGE_ALLOW_FREE_MODELS=on` is only for free ones. A model from another provider is
  refused for now (it would need its own key and model host). The draft's evidence and the
  companion pull request name the model that wrote the tests.
- `./chalkeus forge doctor --target <name>` shows whether auto-draft is on, and the author's
  model: `author model` is information while drafts use the worker's model, and passes once
  the provider accepts its key for the author's model.
- The session that drives runs (your coding agent with the forge skill) never starts the
  watcher or reads its drafts.

### Step mode: leave it running

Step mode carries items through every automatic step and stops at each of your decisions, so
you can leave it running and answer from GitHub. You start it in **your own terminal**:

```sh
./chalkeus forge step --target greeting           # Ctrl-C stops it
./chalkeus forge step --target greeting --once    # one pass, then exit
```

It needs GitHub approvals on for the target (`FORGE_GITHUB_APPROVALS=on`, in its profile or in
`forge.env`; item issues follow, as for runs) and `FORGE_APPROVERS` in `forge.env`.

1. **Propose an item:** add the label "chalkeus:proposed" to the item's GitHub issue. Set
   `FORGE_PROPOSE_LABEL` to use another name. The label counts only when an approver added it
   last, so anyone else labelling the issue starts nothing.
2. **Each pass** (every `FORGE_STEP_INTERVAL_S`, default 120 s), for the first proposed item in
   roadmap order:
   - **No hidden tests:** with auto-draft on, it drafts them as `author watch` does. Otherwise
     it comments once on the issue that tests are needed. You review and merge the tests PR.
   - **Tests merged:** it runs `doctor --baseline` and comments the findings if it fails. If
     it's clean, it starts the run, which waits for your `/approve mode` on its tracking issue.
   - **While the run waits for you** (mode, retries, the item PR, the status PR), it waits too.
   - **When the run succeeds,** it moves to the next proposed item. For an item built in
     slices (`FORGE_SLICE_RUNS=on`), it moves to the item's next slice first
     ([one slice at a time](#one-slice-at-a-time)).
3. **When something fails,** it comments once and leaves the item:
   - a failed `doctor` is tried again when the target or the companion changes;
   - a failed or abandoned run is tried again when you add the label again.

It starts by explaining itself. After each pass that changes something, it prints a `next:`
line: what you do next, with the link, or that it's working and you don't need to do
anything, plus when it checks again. For example:

```text
next: 010: add the label "chalkeus:proposed" to https://github.com/you/greeting/issues/47 (next check in 2m0s)
```

One item is in flight per target. Step mode never approves, merges, labels or edits anything.
It keeps no state of its own, so you can stop and restart it at any point. Each decision is in
`step/<target>/decisions.jsonl` under the evidence folder. The coding agent that drives your
runs never starts it, because it may draft hidden tests.

## 3. Check that an item is ready

```sh
./chalkeus forge gate --target greeting --item 002
```

The check needs no cluster. It clones the target, runs `spec status`, reads the companion
repository, and prints the result as JSON. Exit 0 means ready; exit 10 means refused, with the
first failing rule's code. To check changes before you push them, add `--root <dir>`: the check
then uses the committed HEAD of your local checkout instead of the branch on GitHub.

| Code | What to fix |
|---|---|
| `ITEM_NOT_ON_ROADMAP` | The item isn't an active item of the target's roadmap |
| `DEP_UNSATISFIED:<id>`, `ALREADY_VERIFIED`, `UNEVALUABLE:…` | The usual gate reasons (see the [troubleshooting guide](troubleshooting.md)) |
| `ITEM_ERROR_DIAGNOSTIC:<code>` | `spec status` reports an error on the item, such as a missing `spec.md` (`SS_STAGE_FILE_MISSING`); `spec status --explain` says what to fix |
| `ITEM_SPEC_MISSING` / `ITEM_TASKS_MISSING` | Add the spec dir to the roadmap entry, or the missing file |
| `ITEM_OPEN_QUESTIONS` | Resolve the spec's clarification markers, or the roadmap open question naming the item |
| `ITEM_NO_ALLOWED_PATHS` / `ITEM_PATHS_TOO_WIDE` | Add or narrow `## Allowed paths` |
| `ITEM_NO_HIDDEN_TESTS` | Add `items/<NNN>/` to the companion repository, or check that your git access can read it |
| `INPUT_TOO_LARGE` | The snapshot exceeds `FORGE_MAX_INPUT_MB` |
| `OPEN_ITEM_PR` | A pilot PR for this item is still open; merge or close it |
| `HIDDEN_TESTS_IN_TARGET` | A hidden test's content is already in the target; remove it (see [hidden tests: who can see what](#hidden-tests-who-can-see-what-and-why)) |

### Check everything at once: `./chalkeus forge doctor`

`gate` stops at the first problem. Before you prepare tests or start a run, `doctor` lists
**every** problem in one pass, and changes nothing:

```sh
./chalkeus forge doctor --target greeting                       # profile, cluster, GitHub access
./chalkeus forge doctor --target greeting --item 002            # plus every readiness rule for the item
./chalkeus forge doctor --target greeting --item 002 --baseline # plus, on the cluster, offline:
                                                           # the install and test commands pass today
```

- **Profile:** the target's file, modes, keys and pinned toolchain; the test author's token at
  the recommended level.
- **Cluster:** `./chalkeus forge up` completed, its images match `pilot/images.lock`, a model host is
  set.
- **GitHub:** your token reads the target and the companion; the test author's identity for the
  level; a warning if the target's branch isn't protected (or can't be checked).
- **Roadmap** (every run of `doctor`): the target's progress (verified items out of active
  ones), `spec status`'s own findings (for example `SS_STATUS_AHEAD_OF_TASKS`), and for each item
  what the pilot needs next: `done`, `ready to run`, or what's missing (dependencies, a spec,
  tasks, allowed paths, hidden tests). It never fails `doctor`; use it to pick the next item.
- **CI** (every run of `doctor`, when the target has `.github/workflows/`): a read-only review of
  the target's CI, with CI's exact commands next to forge's ([below](#doctors-ci-review)).
- **Item:** every readiness rule, with each failure's detail (for example the snapshot size), and
  the hidden tests' coverage.
- **`--baseline`:** the project's tests pass on today's code with no network (the check that
  catches a test suite needing a database or the internet), and the hidden tests, if any, fail.
  It never shows hidden-test output.

Exit 0 means no failures (warnings allowed); exit 1 means at least one failure.

### Doctor's CI review

Grading runs the profile's `FORGE_TEST_COMMAND`; the project's CI may run more, or run it
differently. Whenever the target has CI configuration, `doctor` reads it (GitHub Actions for now,
with your read token; nothing is changed or re-run) and reports, as warnings and information only:

| Row | What it tells you | What to do |
|---|---|---|
| `workflows` | which workflows check changes (push or pull request); release, tag-only, schedule and manual workflows are listed but not compared | nothing |
| `default branch` | each job whose latest run on the default branch failed, with the failed step, its command and the telling log line (an advisory, a failing test, a compiler error) | fix it first: a forge baseline fails on it too, or every PR inherits the red check; a vulnerable dependency fits a [dependency item](#a-dependency-upgrade-as-an-item). A deployment or credentials failure is information |
| `test command` | CI's test commands and forge's, each resolved through `package.json` scripts, and whether they agree on coverage and on force-exit or the race detector | make `FORGE_TEST_COMMAND` match CI, or change CI ([strategies](strategies.md#3-grade-the-way-ci-does)) |
| `checks grading doesn't run` | typecheck, lint, build, audit, commit lint and scanning steps that CI runs and grading doesn't | add the ones a change can break to `FORGE_TEST_COMMAND` (for example `npm run typecheck && npm run lint && npm run test:ci`), or accept the gap |
| `runtime` | the Node, Go or Java versions CI sets up, against the target's toolchain | align CI or the toolchain in a planning PR |

documcp's first review (2026-11-27) found the Security Audit job red on `main` (zod < 4.6.6, high)
and that CI's typecheck and lint never ran in grading.

## 4. Run the item

With the cluster up (`./chalkeus forge up`):

```sh
./chalkeus forge run --target greeting --item 002
```

The run follows the fixture's steps, for one item:

1. **Readiness:** the checks above. A refusal exits 10, and nothing starts.
2. **Mode approval.** The mode is shown with the target, item, toolchain and the hosts the
   worker may reach (`model host(s) N` and your registries). Approve it in the terminal, through
   your agent's harness, or on GitHub with `/approve mode` if GitHub approvals are on for the
   target (`FORGE_GITHUB_APPROVALS=on` in its profile).
3. **Prepare.** The pilot snapshots the target at the checked commit (one commit, no history)
   and reads the item's hidden tests from the companion repository. The hidden tests go only to
   the grader; the evidence keeps their names and hashes in `companion.json`, never their
   contents.
4. **Baseline.** On the unchanged code, your test command must pass and the hidden tests must
   fail. Otherwise the run stops before any model spend.
5. **Attempts.** The agent works on the snapshot. Each attempt is graded on:
   - the allowed paths;
   - the item's tasks being ticked;
   - your test command;
   - the same command with the hidden tests copied in.

   A failed attempt waits for your retry approval, as for the fixture.
6. **Draft PR.** The passing change is replayed onto the real base revision, exactly as graded,
   and opened as a draft PR on the target by the publisher. **You review and merge it.**
7. **Status change.** After your merge, `./chalkeus forge resume --run <id>` (or the watcher) proposes
   the item's one-line roadmap change to `verified`. Approve it in the terminal, or merge the
   status-change PR on GitHub.
8. **Audit.** The run ends with the audit. Item runs use the item-run versions of AU01, AU02,
   AU03 and AU11 (only this item, the baseline, one PR, no induction), and AU04 also requires
   that no hidden test reached the worker (P11).

### One slice at a time

A large item can be built and reviewed one user story at a time. Each **slice** gets its own run
and its own draft PR. The item is still the unit that is verified: the status change comes once,
after its last slice.

- **Where slices come from:** the phases of the item's approved `tasks.md`, as spec-status
  (0.4.0 or later) reports them. Each `## Phase N: User Story M …` heading starts slice `USM`.
  Phases before the first story (Setup, Foundational) join the first story's slice, and a phase
  after a story (Polish) joins the slice before it. You decide the split when you approve the
  tasks; the pilot never re-slices. An item with no story phases runs whole, as before.
- **See them:** `./chalkeus forge slices --target greeting --item 006` lists each slice, its state
  (`untouched`, `started`, `merged`) and the current one.
- **Run one:** `./chalkeus forge run --target greeting --item 006 --slice US1`. Without `--slice`
  the whole item runs, exactly as before; an item with a slice already merged must go on slice
  by slice (`ITEM_PARTLY_SLICED`).
- **Order:** slices run in `tasks.md` order. A slice starts only when every earlier slice is
  merged on the default branch (its tasks are ticked there) and has no open PR.
- **Allowed paths per slice:** add `## Allowed paths (US2)` to the spec, in the same list form as
  `## Allowed paths`. A slice without its own list uses the item's.
- **Hidden tests per slice:** `items/006/US1/`, `items/006/US2/` and so on in the companion,
  each laid out like the project. An unsliced item keeps `items/006/`. A slice's grading also
  re-runs every earlier slice's hidden tests (G8), so a later slice can't break an earlier one.
- **What a slice's PR does:** it is titled `feat(006): <title> (US1)`, builds and ticks only
  that slice's tasks, and says `Part of #N` (only the last slice's PR closes the item's issue).
  After you merge a slice before the last, the run records it and proposes **no** status change;
  it prints which slice is next.
- **Item acceptance:** if the spec has `## Item acceptance` (a list, for example "a human checks
  the stock page"), the status change after the last slice waits until you approve
  `acceptance` (`/approve acceptance` on GitHub, or in the terminal).
- **Audit:** each slice run audits on its own, plus AU13 (slice order). `./chalkeus forge audit
  --target greeting --item 006` lists every local run of the item.

**Step mode and automatic drafting** build every item whole unless you turn slices on for the
target with `FORGE_SLICE_RUNS=on` in its profile (off by default, because almost every Spec Kit
`tasks.md` has user-story phases, and existing companions keep their tests in `items/NNN/`). With
it on, they follow each item's current slice: they draft its hidden tests into `items/NNN/USn/`,
run `doctor --baseline --slice` and `run --slice`, and go on to the next slice after you merge.
Each slice run still waits for your `/approve mode`.

`./chalkeus forge resume` and `./chalkeus forge approve` take only `--run`: a paused run always continues
against the target it started with. If that target's profile now names another repository, the
pilot refuses to continue.

**Publishing credential:**
- **GitHub App:** install it on the target too; the pilot mints a token for that repository only.
- **Token mode:** give each target its own fine-grained token in
  `~/.config/chalkeus/targets/<name>.publisher.env` (`PILOT_SCM_TOKEN=…`, mode 0600).
