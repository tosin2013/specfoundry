# Your own repositories (targets)

The fixture shows the pilot's guarantees on two built-in items. A **target** is one of your own
repositories. You prepare its items with Spec Kit; the pilot then runs only items that are
prepared, under the same guarantees. This page covers configuring targets, checking whether an item
is ready, and running it (roadmap item 014). Today you can use `PILOT_TOOLCHAIN=python3.13`, with
packages installed from PyPI, or the built-in `python` (Python 3.11 with pytest) for a project
whose tests need no packages. The other toolchains follow.

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
  - The pilot reads them on your machine with your own git access, and gives them only to the
    grader. The agent never sees them.
  - They must fail on the current code.
  - They may only use dependencies the project's build already declares.

## 2. Configure the target

Target settings live on your machine, never in the target repository. They go in a `targets`
folder next to `pilot.env`:

```text
~/.config/specfoundry/              # or $SPECFOUNDRY_CONFIG, if you set it
├── pilot.env                       # shared: model, approvers, publisher mode
├── publisher.env                   # token mode only: the fixture's token
└── targets/                        # you create this folder; the pilot doesn't
    ├── greeting.env                # the profile for `--target greeting`
    └── greeting.publisher.env      # optional: this target's own token (section 4)
```

- **The file name is the target's name.** `--target greeting` reads `targets/greeting.env`.
  A name is lower-case letters, digits and `-`.
- **Create the folder and the file yourself, readable only by you.** For example, on a machine
  where your home is `/home/ubuntu`, the full path is
  `/home/ubuntu/.config/specfoundry/targets/greeting.env`:

```sh
install -d -m 0700 ~/.config/specfoundry/targets
install -m 600 /dev/null ~/.config/specfoundry/targets/greeting.env
$EDITOR ~/.config/specfoundry/targets/greeting.env
```

- **If the file is missing**, the pilot stops with `TARGET_UNKNOWN: no target "greeting":
  create …/targets/greeting.env`, and prints the full path it looked for.

The profile's contents:

```sh
PILOT_TARGET_REPO=you/greeting-service
PILOT_TARGET_BRANCH=main
PILOT_TOOLCHAIN=jdk21-maven
PILOT_TEST_COMMAND=mvn -B test
PILOT_REGISTRY_HOSTS=repo.maven.apache.org
PILOT_COMPANION_REPO=you/greeting-service-acceptance
PILOT_GITHUB_ISSUES=off
```

- **Your repository declares none of this.** No agent change or merged PR can widen what the
  worker may reach.
- **`PILOT_TOOLCHAIN`** names a toolchain specfoundry builds: `jdk21-maven`, `node24`,
  `python3.13` or `go` (`pilot/images/toolchains.json`). Until its image is published, the pilot
  refuses with `TOOLCHAIN_UNAVAILABLE`.
- **Dependencies:** list the package registries in `PILOT_REGISTRY_HOSTS` and set
  `PILOT_INSTALL_COMMAND`. The install runs twice: once for the agent (with the registries
  reachable), and once, before any attempt, into a cache built from your unchanged code plus the
  hidden tests. The grader then runs offline from that cache, so **an attempt can't add
  dependencies**; add new ones to the project yourself when you prepare the item. For Python
  (`python3.13`):

  ```sh
  PILOT_TOOLCHAIN=python3.13
  PILOT_REGISTRY_HOSTS=pypi.org,files.pythonhosted.org
  PILOT_INSTALL_COMMAND=pip install -r requirements.txt      # dependencies only, not -e .
  PILOT_TEST_COMMAND=PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests
  ```

  The packages go into a virtual environment the pilot creates; your tests must find the project's
  own code through `PYTHONPATH` or your pytest configuration.
- **Any other language:** bring your own toolchain image (next section), or ask for one with the
  [toolchain image request form](https://github.com/tosin2013/specfoundry/issues/new?template=toolchain-image.yml).
- **Optional keys** may only raise the toolchain's defaults: `PILOT_GRADER_MEMORY`,
  `PILOT_GRADER_DEADLINE_S` and `PILOT_CACHE_SIZE`. `PILOT_MAX_INPUT_MB` (default 50) limits
  the repository snapshot.
- **The target repository can't be this one or any target's companion.** The pilot refuses
  with `TARGET_IS_CANARY`.

### Your own toolchain image

A toolchain image only supplies a language's tools. It holds `/opt/toolchain/` with a
`toolchain.json` describing them. The pilot copies them into the agent's and the grader's
pods; the agent's sandbox and the grader stay specfoundry's own images. The format is in
[the toolchain image contract](../specs/014-any-project/contracts/toolchain-image.md). A
template is coming: a UBI Dockerfile for Red Hat and OpenShift, a Debian one for elsewhere, and
a GitHub Actions workflow that builds and attests the image.

```sh
PILOT_TOOLCHAIN=rust-1.83
PILOT_TOOLCHAIN_IMAGE=quay.io/you/toolchain-rust@sha256:<64 hex>
```

- The image must be pinned by digest; a tag is refused.
- Its name can't be one of specfoundry's toolchains.
- The mode approval shows it as operator-supplied, and the run's evidence records it so.
- It runs your project's tests inside the grader, so keep it trustworthy, as you would any base
  image.

List what's configured:

```sh
pilot/pilot targets
```

It prints each target's repository, toolchain, registries and companion, or why the target is
invalid. It never prints a secret or your model host. `fixture` is always listed; it is the
repository in `pilot.env`.

`pilot/pilot reset-fixture` only ever acts on the fixture. With `--target` naming any other
target it refuses with `NOT_A_FIXTURE`, because it force-pushes.

## 3. Check that an item is ready

```sh
pilot/pilot gate --target greeting --item 002
```

The check needs no cluster. It clones the target, runs `spec status`, reads the companion
repository, and prints the result as JSON. Exit 0 means ready; exit 10 means refused, with the
first failing rule's code:

| Code | What to fix |
|---|---|
| `ITEM_NOT_ON_ROADMAP` | The item isn't an active item of the target's roadmap |
| `DEP_UNSATISFIED:<id>`, `ALREADY_VERIFIED`, `UNEVALUABLE:…` | The usual gate reasons (see the [troubleshooting guide](troubleshooting.md)) |
| `ITEM_SPEC_MISSING` / `ITEM_TASKS_MISSING` | Add the spec dir to the roadmap entry, or the missing file |
| `ITEM_OPEN_QUESTIONS` | Resolve the spec's clarification markers, or the roadmap open question naming the item |
| `ITEM_NO_ALLOWED_PATHS` / `ITEM_PATHS_TOO_WIDE` | Add or narrow `## Allowed paths` |
| `ITEM_NO_HIDDEN_TESTS` | Add `items/<NNN>/` to the companion repository, or check that your git access can read it |
| `INPUT_TOO_LARGE` | The snapshot exceeds `PILOT_MAX_INPUT_MB` |
| `OPEN_ITEM_PR` | A pilot PR for this item is still open; merge or close it |

## 4. Run the item

With the cluster up (`pilot/pilot up`):

```sh
pilot/pilot run --target greeting --item 002
```

The run follows the fixture's steps, for one item:

1. **Readiness:** the checks above. A refusal exits 10, and nothing starts.
2. **Mode approval.** The mode is shown with the target, item, toolchain and the hosts the
   worker may reach (`model host(s) N` and your registries). Approve it in the terminal, through
   your agent's harness, or on GitHub with `/approve mode` if GitHub approvals are on for the
   target (`PILOT_GITHUB_APPROVALS=on` in its profile).
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
7. **Status change.** After your merge, `pilot/pilot resume --run <id>` (or the watcher) proposes
   the item's one-line roadmap change to `verified`. Approve it in the terminal, or merge the
   status-change PR on GitHub.
8. **Audit.** The run ends with the audit. Item runs use the item-run versions of AU01, AU02,
   AU03 and AU11 (only this item, the baseline, one PR, no induction), and AU04 also requires
   that no hidden test reached the worker (P11).

`pilot/pilot resume` and `pilot/pilot approve` take only `--run`: a paused run always continues
against the target it started with. If that target's profile now names another repository, the
pilot refuses to continue.

**Publishing credential:**
- **GitHub App:** install it on the target too; the pilot mints a token for that repository only.
- **Token mode:** give each target its own fine-grained token in
  `~/.config/specfoundry/targets/<name>.publisher.env` (`PILOT_SCM_TOKEN=…`, mode 0600).
