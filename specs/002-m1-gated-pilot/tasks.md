---
description: "Task list for 002 — M1 pilot: two-task gate on kind with plain Jobs"
---

# Tasks: M1 pilot — two-task gate on kind with plain Jobs

**Input**: Design documents from `specs/002-m1-gated-pilot/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) (R1–R12),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included. The plan's Testing section and quickstart step 1 require
`python3 -m unittest` coverage of the gate matrix, frame parsing, reconcile rules, the
redaction scan and the audit. The full pilot run is the integration test.

**Organization**: grouped by user story (spec.md). US1 = a blocked task never starts.
US2 = fail, retry, then pass, with publish and merge-gated unblock. US3 = audit from
evidence.

**Conventions**: Python 3.12 **stdlib only**. Every external action is a subprocess call
(`kubectl`, `git`, `spec`, `gh`, `docker`, `kind`). Package root
`pilot/specfoundry_pilot/` (abbreviated `sfp/` below means that path). Secrets are never
read into Python memory: secret env files are only passed by path to `kubectl create
secret --from-env-file` or `grep -F -f`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 / US2 / US3

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton and pinned inputs

- [X] T001 Create the directory layout from plan.md: `pilot/specfoundry_pilot/runner/`, `pilot/images/{worker,tools,egress}/`, `pilot/manifests/`, `pilot/fixture/`, `pilot/grading/`, `pilot/tests/fixtures/`, plus empty `__init__.py` files in `pilot/specfoundry_pilot/` and `pilot/specfoundry_pilot/runner/`
- [X] T002 Create the shim `pilot/pilot` (bash, executable): `cd` to repo root, `export PYTHONPATH=$ROOT/pilot`, `exec python3 -m specfoundry_pilot "$@"`; and `pilot/specfoundry_pilot/__main__.py` calling `cli.main()`
- [X] T003 [P] Create `pilot/pins.env` recording the pins: `KIND_VERSION=v0.27.0`, `KUBECTL_VERSION=v1.32.2`, `CALICO_VERSION=v3.29.3`, `SPEC_VERSION=0.2.0`, `SPEC_COMMIT=be0805319ea0025bb98e55009c13af9b52cdb834`, `OPENCODE_VERSION=2.2.7`, `OPENCODE_SHA256=589253d36810f21217edd51545cd435b328cdc3cf4f451fbe0cce6f88afcf5e1`, and placeholders for `REGISTRY_IMAGE`, `DEBIAN_BASE`, `ALPINE_BASE` digests (filled by T004)
- [X] T004 Resolve and record digests (R10 *verify at implement*): `docker pull` then `docker inspect --format '{{index .RepoDigests 0}}'` for `registry:2`, `debian:bookworm-slim` and `alpine:3.20`. Write the `name@sha256:…` values into `pilot/pins.env`, and note the resolution date in `specs/002-m1-gated-pilot/research.md` under R10
- [X] T005 [P] Add `.gitignore` entries: `__pycache__/`, `*.pyc`, `pilot/.build/`, `*.env` (but not `pilot/pins.env`, via `!pilot/pins.env`)
- [X] T006 [P] Create `pilot/kind-config.yaml`: cluster name `specfoundry-m1`, `disableDefaultCNI: true`, `podSubnet: 192.168.0.0/16`, a single control-plane node, and a `containerdConfigPatches` registry mirror mapping `localhost:5001` → `http://specfoundry-registry:5000` (kind local-registry pattern)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, evidence, kubectl helpers, the CLI skeleton, and cluster up/down. Every story needs these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T007 [P] Implement `pilot/specfoundry_pilot/config.py` per contracts/config.md:
  - load `pilot.env` from `${SPECFOUNDRY_CONFIG:-~/.config/specfoundry}`, plus the paths (not contents) of the `opencode/` credential directory and `publisher.env` (contracts/config.md)
  - refuse any of the three files that is not mode `0600`
  - **repo guard**: `PILOT_FIXTURE_REPO` name must end in `-pilot-fixture` and must differ from this repo's `git remote get-url origin` (else exit 3)
  - **opencode/ checks**: dir `0700`, files `0600`; only `opencode.json` + `*_api_key` are used; reject SCM-like file names (`GITHUB|^GH_|GIT_.*TOKEN`) and any literal secret in `opencode.json` (only `{file:...}`/`{env:...}` references allowed)
  - defaults: `PILOT_SPEND_CAP_USD=1.00`, `PILOT_TOKEN_CAP=2000000`, `RETRY_LIMIT=2` (values >2 rejected)
- [X] T008 [P] Implement `pilot/specfoundry_pilot/evidence.py`:
  - `new_run()` creates `specs/002-m1-gated-pilot/evidence/<YYYYMMDDTHHMMSSZ>/` with the layout in contracts/evidence-record.md
  - `event(stage, task, attempt, event, detail)` appends `{seq, at, stage, task, attempt, event, detail}` to `events.jsonl` with a monotonically increasing `seq`
  - `load_run`/`save_run` for `run.json` (data-model "Run" states: `in-progress | paused(awaiting-merge) | failed(reason) | succeeded | torn-down`)
  - `record_check(file, id, requirement, result, description, detail)` writing the 001 row shape
  - `write_config_json()` storing non-secret pilot.env values plus the `sha256sum` of each secret file
- [X] T009 [P] Implement `pilot/specfoundry_pilot/k8s.py`: `kubectl(*args, input=None, check=True)` bound to `--context kind-specfoundry-m1`, `apply(yaml_text)`, `wait_job(ns, name, timeout)` returning `Complete/Failed/DeadlineExceeded/Timeout`, `logs(ns, job)`, `delete_ns(ns, wait=True)`, `create_secret_from_env_file(ns, name, path)` (passes the path only), `can_i(verb, resource, ns, as_sa)`, and `render(template_path, **vars)` doing `${VAR}` substitution with `string.Template.substitute` (missing var = error)
- [X] T010 Implement the CLI skeleton `pilot/specfoundry_pilot/cli.py` with argparse subcommands `up`, `reset-fixture`, `run`, `resume`, `gate`, `audit`, `down`, `status`, and the exit codes from contracts/cli.md (0, 1, 2, 3, 4, 5, 10). Stubs raise `NotImplementedError` → exit 2. Implement `status` (prints `run.json`). `run`/`resume` exit 2 unless the marker `pilot/.build/up.ok` exists
- [X] T011 Implement the cluster part of `pilot up` in `pilot/specfoundry_pilot/cluster.py`:
  - run `test/isolation/tools.sh` (pinned kind and kubectl)
  - start the `specfoundry-registry` container from the `REGISTRY_IMAGE` digest on port `127.0.0.1:5001`
  - `kind create cluster --config pilot/kind-config.yaml`, then `docker network connect kind specfoundry-registry`
  - apply Calico `CALICO_VERSION` (download to `pilot/.build/`, record its sha256), then wait for calico-node, calico-kube-controllers, nodes Ready and coredns
  - write `pilot/.build/up.ok`
- [X] T012 Implement `pilot down` in `pilot/specfoundry_pilot/cluster.py`:
  - delete the kind cluster and remove the registry container; remove `pilot/.build/up.ok`
  - record T01 cluster absent, T02 no kind node containers (label `io.x-k8s.kind.cluster=specfoundry-m1`), T03 registry container absent — into the active run's `teardown.jsonl` (or a standalone `pilot/.build/teardown.jsonl` if no run)
  - exit 1 if any check fails
- [X] T013 Write `versions.txt` in `pilot/specfoundry_pilot/evidence.py` (`write_versions(images)`): kind, kubectl client, server gitVersion, node image, Calico version and sha256, `spec --version`, OpenCode version and sha256, every pilot image digest, `uname -srm`

**Checkpoint**: `pilot/pilot up && pilot/pilot down` creates and verifies teardown of an empty Calico cluster with the registry.

---

## Phase 3: User Story 1 — A blocked task never starts (Priority: P1) 🎯 MVP

**Goal**: The gate evaluates the fixture roadmap through `spec status --json`, allows only a fully ready task, refuses everything else (including unevaluable input), and records every decision. No worker is created on refusal.

**Independent Test**: `python3 -m unittest discover -s pilot/tests -v` passes the fail-closed matrix. Then `pilot/pilot gate B --root pilot/fixture` exits 10 with `DEP_UNSATISFIED:001`, `pilot/pilot gate A --root pilot/fixture` exits 0, and both decisions validate against contracts/gate-decision.schema.json.

### Tests for User Story 1 ⚠️ (write first; they must fail before T019)

- [X] T014 [P] [US1] Create gate test inputs in `pilot/tests/fixtures/status/`: one JSON file per case, derived from a real `spec status --json --root pilot/fixture` capture (after T017):
  - `ready_A.json`
  - `blocked_B.json` (dependency `001` `satisfied:false`, `blocked_count:1`)
  - `ready_B_after_verify.json`
  - `schema_1_1.json`
  - `incomplete.json` (`complete:false`)
  - `error_set.json` (`error` non-null)
  - `item_missing.json`
  - `item_duplicate.json`
  - `status_unknown.json`
  - `inactive.json`
  - `already_verified.json`
  - `already_implemented.json`
  - `item_error_diag.json` (diagnostic `severity:error` for the item)
  - `inconsistent_count.json` (unsatisfied dependency but `blocked_count:0`)
  - `malformed.txt` (not JSON)
- [X] T015 [P] [US1] Write `pilot/tests/test_gate.py`:
  - for each fixture, assert the `decision` and exact `reasons`
  - assert exit codes 2 and 127 (spec missing) → `refuse` with `UNEVALUABLE:exit_2` / `UNEVALUABLE:spawn_failed`
  - assert stdout of 0 bytes → `UNEVALUABLE:empty`
  - assert `allow` ⇔ `reasons == ["OK"]`
  - validate every produced decision against `contracts/gate-decision.schema.json` with a minimal stdlib checker (required keys, enums, reason regex)
- [X] T016 [P] [US1] Write `pilot/tests/test_config.py`:
  - repo guard: `owner/foo-pilot-fixture` accepted; `owner/specfoundry`, `owner/specfoundry-test` and the origin repo rejected → exit 3
  - mode `0644` rejected
  - an `opencode/` dir with a literal key in `opencode.json`, an SCM-like key file, a missing key file, or mode `0755` rejected
  - `RETRY_LIMIT=3` rejected

### Implementation for User Story 1

- [X] T017 [US1] Create the fixture template `pilot/fixture/` (copied verbatim to the throwaway repo by reset-fixture):
  - `.specify/memory/roadmap.md` in speckit-roadmap format, with items `001 — Slug function [status: planned]` (Spec dir `specs/001-slugify`, Depends on: none) and `002 — Unique slugs [status: planned]` (Spec dir `specs/002-unique-slug`, Depends on: 001), each with Description/Outcome/Scope lines like the specfoundry roadmap
  - `specs/001-slugify/spec.md` describing `slugify(text) -> str` in `src/slugkit/slug.py`, with a section headed exactly `## Acceptance details` that holds non-guessable rules: max length `SLUG_MAX = 37`; separator `~`; an empty result returns the literal `"n~a"`
  - `specs/001-slugify/tasks.md` with 3 unchecked tasks
  - `specs/002-unique-slug/spec.md` describing `unique_slug(text, existing: set[str]) -> str` in `src/slugkit/unique.py` (reuses `slugify`; suffixes `~2`, `~3`…; still ≤ `SLUG_MAX`), with its own `## Acceptance details` section
  - `specs/002-unique-slug/tasks.md` with 3 unchecked tasks
  - `src/slugkit/__init__.py`
  - visible tests `tests/test_visible.py` that check only basic behaviour, not the acceptance details
  - `README.md` stating it is a throwaway pilot fixture
  - then run `spec status --json --root pilot/fixture` and confirm 001 is ready and 002 is blocked
- [X] T018 [P] [US1] Create hidden grading tests in `pilot/grading/`: `test_hidden_001.py` (asserts `SLUG_MAX == 37`, separator `~`, the `"n~a"` empty case, truncation without a trailing separator) and `test_hidden_002.py` (suffix sequence `~2`/`~3`, length ≤ 37 including suffix, no collision with `existing`). These files are never copied to `pilot/fixture/` or any worker input
- [X] T019 [US1] Implement `pilot/specfoundry_pilot/gate.py` per research R3:
  - `evaluate(task_label, item_id, root, seq) -> dict`, which runs `spec status --json --root <root>` with a 60 s timeout
  - apply rules 1–7 in order, collecting reasons with the exact codes from contracts/gate-decision.schema.json; startable statuses are only `planned|specced|in-progress`
  - store the raw stdout as `<seq>-<task>.status.json` and its sha256 in `input.spec_status_json_sha256`
  - any Python exception inside evaluation is caught → `refuse` with `UNEVALUABLE:internal`
- [X] T020 [US1] Implement `fresh_clone(repo, branch) -> (path, commit)` in `pilot/specfoundry_pilot/fixture.py`: `gh repo clone <repo> <tmp> -- --depth 1 --branch <branch>` (operator's read auth), returns the HEAD sha. On any failure, the caller's gate decision becomes `refuse` with `UNEVALUABLE:clone_failed`
- [X] T021 [US1] Implement `pilot gate <A|B> [--root DIR]` in `pilot/specfoundry_pilot/cli.py`: with `--root`, evaluate that directory; otherwise use `fresh_clone`. Print the decision JSON, append it to the active run's `gate/` if a run is active, and exit 0 for allow, 10 for every refuse
- [X] T022 [US1] Implement `pilot reset-fixture [--yes]` in `pilot/specfoundry_pilot/fixture.py`:
  - apply the repo guard (T007)
  - show the target repo and require typed `y` unless `--yes`
  - clone, replace the tree with `pilot/fixture/`, commit `pilot: reset fixture`, `git push --force` to `PILOT_FIXTURE_BRANCH` using the operator's git auth
  - close every open PR whose head starts with `pilot/` (`gh pr close`) and delete those remote branches
  - record the new base revision in `pilot/.build/fixture-base.txt`

**Checkpoint**: The US1 independent test passes. The gate is proven fail-closed with no cluster involved.

---

## Phase 4: User Story 2 — A failed grade keeps the dependent blocked, a retry recovers (Priority: P1)

**Goal**: The full pilot: A/1 fails grading (induced), B stays refused, A/2 passes, one draft PR for A, pause for human merge, reconcile plus approval sets A verified, the gate opens B, B passes, one draft PR for B.

**Independent Test**: quickstart.md steps 2–4 on a fresh cluster. `events.jsonl` shows A/1 fail → A/2 pass → PR A → B refused → (merge, approve) → B allowed → B pass → PR B, with exactly 2 draft PRs on the throwaway repo.

### Tests for User Story 2 ⚠️ (write first)

- [X] T023 [P] [US2] Write `pilot/tests/test_frame.py` for `decode_frame(log_text)` (contracts/worker-io.md):
  - a valid frame is accepted
  - rejected with a reason code: missing BEGIN → `no_result`; two frames → `bad_frame`; decoded size > 512 KiB → `oversize`; sha256 mismatch → `bad_frame`; text after END is ignored but the BEGIN line must be exactly `PILOT-RESULT-BEGIN v1`
  - a tar without `report.json` → `bad_frame`
- [X] T024 [P] [US2] Write `pilot/tests/test_prompt.py` for `build_prompt(spec_md, tasks_md, induction)`:
  - with `induction="withheld-acceptance-section"`, the text from `## Acceptance details` up to the next `## ` heading is removed and nothing else changes
  - with `None`, the prompt contains the full spec
  - raises if the induction is requested but the heading is absent
- [X] T025 [P] [US2] Write `pilot/tests/test_reconcile.py` with stubbed subprocess results:
  - proposal only when `pr_merged` and `tasks_percent==100` and every changed path matches the graded head
  - mismatch → no proposal, reason `TREE_MISMATCH`
  - not merged → exit 4
  - operator `N` → exit 5 and no push
  - the applied edit changes exactly one line: `[status: planned]` → `[status: verified]` on the item's heading
- [X] T026 [P] [US2] Write `pilot/tests/test_publisher_idempotency.py`: given a stubbed open-PR listing for head `pilot/<run>/a`, `publish()` records `created:false` and creates nothing; given an empty listing, it creates exactly one PR with `draft:true`

### Images (R10)

- [X] T027 [P] [US2] Create `pilot/images/worker/Dockerfile`:
  - `FROM ${DEBIAN_BASE}` (digest); `apt-get install --no-install-recommends git ca-certificates python3`, pinned to exact versions from `apt-cache policy` (record them in a comment)
  - `COPY opencode /usr/local/bin/opencode`; verify with `sha256sum -c` against `OPENCODE_SHA256` at build time
  - user `worker` uid 10001, `HOME=/home/worker`; no sudo
  - `COPY entrypoint.sh watchdog.py /usr/local/lib/pilot/`; `ENTRYPOINT ["/usr/local/lib/pilot/entrypoint.sh"]`
- [X] T028 [US2] Verify OpenCode v2.2.7 behaviour (R2/R4 *verify at implement*) using the built worker image locally (`docker run` with the operator's OpenCode config files mounted at `$HOME/.config/opencode` and a scratch repo):
  - which `--format json` event fields carry cost and tokens
  - whether `--standalone` is needed for a headless single run
  - which env/config disables autoupdate, model-catalogue fetch and sharing
  - that `HTTPS_PROXY` is honoured
  - record the findings in research.md R2/R4 (and the token-only downgrade if no cost field exists)
- [X] T029 [US2] Write `pilot/images/worker/watchdog.py`: read OpenCode JSON events line by line from stdin and tee them to `/tmp/harness.jsonl`; accumulate cost and tokens using the fields found in T028; if `cost ≥ PILOT_SPEND_CAP_USD`, or (cost stays 0 and `tokens ≥ PILOT_TOKEN_CAP`), send SIGTERM to the harness pid given in argv and set `stopped_by_cap`; at EOF write `/tmp/spend.json` `{cap_usd, cap_mode: cost|token-fallback, cost_usd, tokens, stopped_by_cap}`
- [X] T030 [US2] Write `pilot/images/worker/entrypoint.sh` per contracts/worker-io.md:
  - `set -euo pipefail`; redirect all its own diagnostics to `/tmp/entry.log` (fd 1 is reserved for the frame)
  - `git clone /in/base.bundle /work/repo`; check out `base_revision` from `/in/meta.json`
  - run `opencode run --format json --auto --model "$PILOT_MODEL" "$(cat /in/prompt.md)"` piped through `watchdog.py`
  - `git add -A && git commit` as `pilot-worker`; `git bundle create /tmp/out/change.bundle <base>..HEAD`
  - build `report.json` (version 1, harness exit, spend from `/tmp/spend.json`, `changed_paths`, a 4 KiB redacted `log_tail` with key-like strings `sk-…`/`ghp_…`/`github_pat_…` masked)
  - tar both files and print the frame with its sha256; on any failure still emit a frame with `report.json` carrying the error and no bundle
- [X] T031 [P] [US2] Create `pilot/images/tools/Dockerfile`:
  - `FROM ${DEBIAN_BASE}`; pinned `git python3 python3-pytest curl ca-certificates`
  - `COPY spec /usr/local/bin/spec`, verified against the recorded sha256 of the host binary (add `SPEC_SHA256` to `pilot/pins.env`)
  - uid 10002, no sudo; `COPY grade.sh publish.sh /usr/local/lib/pilot/`
- [X] T032 [P] [US2] Create `pilot/images/egress/Dockerfile` (`FROM ${ALPINE_BASE}`, `apk add tinyproxy=<pinned>`, non-root uid 10003) and `pilot/images/egress/tinyproxy.conf.tmpl`: `Port 8888`, `FilterDefaultDeny Yes`, `FilterType` set for exact-host matching, `ConnectPort 443` only, `LogLevel Connect`. Verify the exact-host filter syntax for the pinned tinyproxy version (R4 *verify at implement*) and note the result in research.md R4
- [X] T033 [US2] Implement the image part of `pilot up` in `pilot/specfoundry_pilot/images.py`:
  - copy the OpenCode binary and `spec` binary into `pilot/.build/` contexts
  - `docker build` with `--build-arg` digests from `pilot/pins.env`
  - push to `localhost:5001/pilot-{worker,tools,egress}:<git-short-sha>`
  - resolve each pushed digest (`docker inspect` RepoDigests) and write `pilot/.build/images.json` `{worker, tools, egress: "localhost:5001/…@sha256:…"}`; all manifests consume only these digest refs

### Manifests

- [X] T034 [P] [US2] Create `pilot/manifests/egress.yaml.tmpl`: namespaces `pilot-egress-model` and `pilot-egress-scm`, each with a tinyproxy Deployment (1 replica, the egress image digest, hardened securityContext as 001, a ConfigMap from `tinyproxy.conf.tmpl` and an allowlist of `${MODEL_HOSTS}` or `github.com`+`api.github.com`) and a Service on port 8888. NetworkPolicies:
  - model proxy ingress only from namespaces labelled `specfoundry.io/role=worker`
  - SCM proxy ingress only from `specfoundry.io/role=publisher`
  - both proxies: egress to DNS and `0.0.0.0/0` port 443 except the cluster pod/service CIDRs
- [X] T035 [P] [US2] Create `pilot/manifests/worker.yaml.tmpl` (with a `${UNIT}` switch: `job` renders the worker Job, `probe` renders the probe-twin sleep pod for T054) for namespace `${NS}` (label `specfoundry.io/role=worker`):
  - SA with `automountServiceAccountToken:false`
  - ResourceQuota `pods:"1"`, `count/secrets:"1"`, `count/configmaps:"2"` (inputs + kube-root-ca), cpu/memory caps as 001; LimitRange
  - default-deny NetworkPolicy, plus egress only to kube-dns 53 and `pilot-egress-model` proxy pods on 8888
  - Job `worker` with `backoffLimit:0`, `activeDeadlineSeconds:1200`, `ttlSecondsAfterFinished` unset (namespace deletion cleans up); pod `automountServiceAccountToken:false`, runAsNonRoot uid 10001, seccomp RuntimeDefault, `readOnlyRootFilesystem:true`, drop ALL, no privilege escalation
  - image `${WORKER_IMAGE}` (digest); `envFrom` Secret `model-key`; env `PILOT_MODEL`, `HTTPS_PROXY`, `NO_PROXY=` empty, spend caps
  - volumes: ConfigMap `inputs` at `/in` read-only; emptyDirs `/work` (512Mi), `/home/worker` (256Mi), `/tmp` (256Mi)
- [X] T036 [P] [US2] Create `pilot/manifests/grader.yaml.tmpl` for namespace `${NS}` (label `specfoundry.io/role=grader`):
  - SA no automount; quota `count/secrets:"0"`, `pods:"1"`
  - default-deny NetworkPolicy with **no egress rules** (no DNS either)
  - Job `grader` with `backoffLimit:0`, `activeDeadlineSeconds:300`, image `${TOOLS_IMAGE}`, command `grade.sh`, hardened as above
  - ConfigMaps `submission` (bundle, meta) at `/in` and `grading` (hidden tests from `pilot/grading/`) at `/grading`, both read-only; emptyDir `/tmp`
- [X] T037 [P] [US2] Create `pilot/manifests/publisher.yaml.tmpl`:
  - namespace `pilot-publish` (label `specfoundry.io/role=publisher`), SA no automount, quota `pods:"1"`, `count/secrets:"1"`
  - NetworkPolicy egress only to DNS and the `pilot-egress-scm` proxy
  - Job `publish-${TASK}-${RUN_SHORT}` with `backoffLimit:0`, `activeDeadlineSeconds:300`, image `${TOOLS_IMAGE}`, command `publish.sh`, env from Secret `scm-token`, `HTTPS_PROXY` set to the SCM proxy
  - ConfigMap `pub-${TASK}` (bundle, `pr.json` with title/body/head/base) at `/in`

### Grader, publisher and worker orchestration

- [X] T038 [US2] Write `pilot/images/tools/grade.sh`. Clone the fixture base from `/in/base.bundle`, fetch `/in/change.bundle`, then run in order:
  - G1: `git bundle verify` and the fetched head fast-forwards from `base_revision`
  - G2: changed paths are within `allowed_paths` from `/in/meta.json`
  - G3: `spec status --json --root .` shows the task item's `tasks.percent == 100`
  - G4: `python3 -m pytest -q tests/`
  - G5: `python3 -m pytest -q /grading/test_hidden_<item>.py` with `PYTHONPATH=src`
  Later checks are marked `skipped` after a failure. Emit `grade.json` (contracts/grade-report.schema.json) in the same stdout frame format as the worker, with `grader_image` from env
- [X] T039 [US2] Write `pilot/images/tools/publish.sh` (R8; verify fine-grained token permission names and the REST `draft` field):
  - clone `https://x-access-token:${PILOT_SCM_TOKEN}@github.com/${REPO}.git` via the proxy using `GIT_ASKPASS` (the token is never put on a command line or in logs)
  - check `GET /repos/{repo}/pulls?head={owner}:{head}&state=open`; if present, print it and exit 0 with `created:false`
  - else apply the bundle onto `base`, push `pilot/<run>/<task>`, then `POST /repos/{repo}/pulls` with `draft:true`, title `pilot <run> task <A|B>`, and the body from `/in/pr.json`
  - print a stdout frame with `{number, url, head, draft, author, created}`; there is no merge call anywhere
- [X] T040 [US2] Implement `pilot/specfoundry_pilot/runner/base.py` (abstract `Runner`: `submit(unit_kind, ns, manifest) -> handle`, `wait(handle, timeout) -> outcome`, `collect(handle) -> log_text`, `delete(handle)`) and `pilot/specfoundry_pilot/runner/jobs.py` (plain Jobs backend using `k8s.py`; `wait` maps Job conditions and pod reason `DeadlineExceeded` to outcomes; `delete` deletes the namespace and waits for it to go)
- [X] T041 [US2] Implement `pilot/specfoundry_pilot/worker.py`:
  - `build_prompt` (T024)
  - `make_inputs(task, attempt)`: `git bundle create` of the base revision, `prompt.md`, and `meta.json` with `allowed_paths` (`src/slugkit/**`, the task's `specs/<dir>/tasks.md`, `tests/**`)
  - `decode_frame` (T023)
  - `run_attempt(task, n)`: namespace `pilot-w-<task>-<n>`; render and apply `worker.yaml.tmpl`; create Secret `model-key` `--from-file` from the `opencode/` files and mount it read-only at `/home/worker/.config/opencode`; record live checks via `checks.run_worker_checks` (T055) while running; wait; collect the frame; save `prompt.md`, `meta.json`, `induction.json` (when induced: `{name, removed_heading, removed_sha256, removed_bytes}`), `change.bundle`, `report.json`, `job.json` and `proxy-denials.log` (tinyproxy log lines for the attempt window) into `attempts/<task>-<n>/`; delete the namespace
  - the induction is `withheld-acceptance-section` exactly when task A and n==1; record it in `events.jsonl`
  - attempt state transitions as in the data-model state machine
- [X] T042 [US2] Implement `pilot/specfoundry_pilot/grader.py` `grade(task, n, bundle)`: namespace `pilot-g-<task>-<n>`; ConfigMaps `submission` and `grading`; apply `grader.yaml.tmpl`; wait 300 s; decode the frame; on timeout, missing frame or crash write a `grade.json` with `result:"fail"` and `failure` set to `grader_timeout|grader_error|no_result|bad_frame`; delete the namespace
- [X] T043 [US2] Implement `pilot/specfoundry_pilot/publisher.py` `publish(task, passing_attempt)`:
  - refuse unless that attempt's `grade.json.result=="pass"` (FR-012)
  - build `pr.json`; the body has the evidence summary (run id, attempt list with grades, gate decision seqs, image digests, spend)
  - run the Job, decode the frame, append to `prs.json` with `attempt`; enforce at most one entry per task (a second call returns the existing entry)
  - after the call, verify via `gh pr view --json isDraft,author` that `draft==true` and author ≠ operator login (`gh api user`)
- [X] T044 [US2] Make publishing resumable in `pilot/specfoundry_pilot/pipeline.py` and `pilot/specfoundry_pilot/publisher.py`:
  - before calling `publish`, set the task state to `publishing` in `run.json`
  - on Job failure, deadline or a bad frame, set it to `publish-failed`, save the run as `paused(awaiting-publish)` and exit 1; the task is never recorded verified and B stays gated
  - `pilot resume` re-runs `publish(task, passing_attempt)` using `attempts/<task>-<n>/change.bundle`
  - T026 gains a case: a first call fails after the PR is created, and the re-run finds it and records `created:false`
- [X] T045 [US2] Implement `pilot/specfoundry_pilot/reconcile.py` (R9):
  - `check(task)`: `gh pr view <n> --json state,mergedAt,mergeCommit`; `fresh_clone`; `spec status --json` → `tasks.percent`; compare each `changed_path` at the default branch with the graded head blob (`git cat-file` from the stored bundle)
  - `propose()` prints the one-line diff; `approve()` reads `y/N` from a TTY; `apply()` edits the clone, commits `pilot: <item> verified (run <id>)` and `git push`es with the operator's auth
  - write `reconcile/<task>.json`
- [X] T046 [US2] Implement `confirm_mode(run)` in `pilot/specfoundry_pilot/pipeline.py`:
  - print the mode `{name: "step-by-step", retry_limit, spend_cap_usd, token_cap, worker_deadline_s: 1200}`
  - require a typed `y`; `N`, EOF or no TTY exits 5 with no worker staged
  - record event `mode_confirmed` and `run.json.mode`
  - `pilot run` calls it after the two initial gate checks and before attempt A/1
- [X] T047 [US2] Implement `pilot run` in `pilot/specfoundry_pilot/pipeline.py` and wire it in `cli.py`:
  - precondition: `gh pr list -R $PILOT_FIXTURE_REPO --state open --json headRefName` returns no head starting with `pilot/`; otherwise exit 2 with "run reset-fixture first"
  - new run; `write_config_json`, `write_versions`; record `base_revision` from `pilot/.build/fixture-base.txt`
  - gate A (fresh clone) and stop with exit 1 if refused; gate B and **assert refuse** (if allowed: run failed `B_NOT_BLOCKED`)
  - `confirm_mode(run)` (T046) after the two initial gate checks; exit 5 if not confirmed
  - attempt A/1: `run_attempt` → `grade`. After every failed attempt, re-gate B and assert refuse. Then, if attempts remain, call `confirm_retry(task, n)`:
    - it prompts `Retry <task> (attempt n of 3)? [y/N]` on the TTY
    - `y` records event `retry_confirmed` and starts the next attempt
    - `N`, EOF or no TTY records `retry_declined`, saves `run.json` as `paused(awaiting-retry)` and exits 6
    - stop on pass
  - if all fail: run `failed(A_RETRIES_EXHAUSTED)`, exit 1, B never attempted
  - `publish(A)`; gate B again (must refuse: PR not merged); save `run.json` as `paused(awaiting-merge)`; print the PR URL and the instruction to merge then `pilot resume`; exit 0
- [X] T048 [US2] Implement `pilot resume [--run ID]` in `pilot/specfoundry_pilot/pipeline.py`:
  - load the paused run; `reconcile.check(A)` (not merged → exit 4, run stays paused)
  - propose/approve (N → exit 5, no change); apply; gate B from a fresh clone (refuse → run failed `B_STILL_BLOCKED`, exit 1)
  - when the loaded run is `paused(awaiting-retry)`, re-ask `confirm_retry` for the pending task and continue the same loop; when it is `paused(awaiting-publish)`, re-run publishing (T044)
  - B attempts with the same confirmed-retry loop and no induction; `publish(B)`
  - call `audit.run()` (US3; until US3 lands, skip with event `audit_pending`); mark `succeeded`; write `summary.md`; exit 0
- [X] T049 [US2] Implement the remaining `pilot up` steps in `pilot/specfoundry_pilot/cluster.py`: after T011 and T033, apply `egress.yaml.tmpl` (model hosts from `PILOT_MODEL_EGRESS_HOSTS`) and wait for both proxies; apply the `pilot-publish` namespace parts of `publisher.yaml.tmpl` (namespace, SA, quota, netpol) and create Secret `scm-token` from the `publisher.env` path; write `up.ok` only after all of this succeeds
- [X] T050 [US2] Write `summary.md` generation in `pilot/specfoundry_pilot/evidence.py` (`write_summary(run)`): the ordered event table (seq, stage, task, attempt, event), attempts with grade and spend, PR links, check/audit pass counts, and the known limits from plan.md

**Checkpoint**: A full quickstart run (steps 2–4) produces exactly 2 draft PRs in the fail → retry → pass → merge → B order.

---

## Phase 5: User Story 3 — Credentials and isolation are auditable after the fact (Priority: P2)

**Goal**: Live isolation and credential checks P01–P10 recorded during the run, and an evidence-only audit AU01–AU11 plus a redaction scan that a reviewer can re-run on the committed record.

**Independent Test**: `pilot/pilot audit --run <id>` on a committed evidence directory (with no cluster running) prints AU01–AU11 all pass. Corrupting a copy (e.g. removing a refusal line, adding a fake `ghp_` string, or adding a third PR entry) makes the matching AU check fail.

### Tests for User Story 3 ⚠️ (write first)

- [X] T051 [P] [US3] Create a synthetic evidence directory `pilot/tests/fixtures/evidence-good/` (`events.jsonl`, `prs.json`, `checks/results.jsonl`, `attempts/*/report.json`, `attempts/*/grade.json`, `gate/*.json`, `teardown.jsonl`) for a correct run, plus mutation helpers in `pilot/tests/test_audit.py`
- [X] T052 [P] [US3] Write `pilot/tests/test_audit.py`: the good directory → all AU pass. One mutation per check → exactly that AU fails:
  - AU01 attempt for B before the A-verified event
  - AU02 missing A/1 failure
  - AU03 3 PRs / a non-draft / wrong author
  - AU04 a failed P04 row
  - AU05 a failed matrix row
  - AU06 `cost_usd 1.20` with `stopped_by_cap:false`
  - AU07 a failed T row
  - AU08 a file containing `github_pat_x`
  - AU09 attempt A/2 without `retry_confirmed`
  - AU10 `mode_confirmed` after A/1
  - AU11 A/2's prompt missing the acceptance section
- [X] T053 [P] [US3] Write `pilot/tests/test_redaction.py`: the scanner flags `github_pat_`, `ghp_`, `gho_`, `sk-`, `Bearer ` and exact values from a temp secret env file (via `grep -rF -f <(cut -d= -f2- file)`), and does not flag the file's sha256 recorded in `config.json`

### Implementation for User Story 3

- [X] T054 [US3] Implement `pilot/specfoundry_pilot/checks.py` with a shared probe helper (as 001's `probe`/`noreach`). The worker namespace quota allows only 1 pod, so network probes run in a **probe twin**: namespace `pilot-w-<task>-<n>-probe`, rendered from the same `worker.yaml.tmpl` (same labels, NetworkPolicies and quota) but with a `sleep` pod from the tools image (which has curl) instead of the Job. Probes use `kubectl exec … curl` and the twin is deleted with the attempt. A control pod `pilot-control` (unrestricted, tools image), created by `up`, is used for control probes
- [X] T055 [US3] Implement `run_worker_checks(ns, attempt_dir)` in `pilot/specfoundry_pilot/checks.py`:
  - P01: exactly 1 pod and 1 container
  - P02: SA and pod automount false; no token path
  - P03: default-deny exists; quota `pods=1`, `count/secrets=1`; Job `activeDeadlineSeconds` set
  - P04: the only Secret is `model-key`; env names (from the pod spec plus Secret keys) do not match `TOKEN|GITHUB|^GH_|PASSWORD` except `PILOT_MODEL_API_KEY`
  - P05: no ConfigMap named `grading`, no volume from `/grading`
  - P06: from the probe twin — the model host reachable through the proxy; `https://github.com` through the proxy → denied (403/blocked); `1.1.1.1` direct → blocked; control pod direct to `github.com` → reachable
  - P07: probe twin → `pilot-g-*` grader namespace blocked; control → reachable (use a long-lived `pilot-grader-target` stand-in pod in a namespace labelled grader, created by `up`)
  - P08: `can-i create pods,configmaps,pods/exec -n pilot-g-<task>-<n> --as system:serviceaccount:<ns>:worker` = no
  Write rows to `checks/results.jsonl` with the IDs and requirements from contracts/evidence-record.md
- [X] T056 [US3] Implement `run_cluster_checks()` in `pilot/specfoundry_pilot/checks.py`: P09 scans all namespaces for Secrets with keys matching `PILOT_SCM_TOKEN|TOKEN|GITHUB` — only `pilot-publish/scm-token` is allowed; P10 checks every pod in `pilot-*` namespaces for an `@sha256:` image, runAsNonRoot and `allowPrivilegeEscalation:false`. Call it after each publish and once per attempt from `pipeline.py`
- [X] T057 [US3] Add the gate fail-closed matrix to the run record: in `pipeline.py` `run`, execute the US1 unit matrix (`python3 -m unittest discover -s pilot/tests -p test_gate.py`) and live variants — `gate --root <dir with no .specify>`, `gate` with `SPEC_BIN=/bin/false`, `gate` with a roadmap truncated mid-item — recording each as `checks/results.jsonl` rows `GM01…` (requirement `FR-002`). The run fails if any variant allows
- [X] T058 [US3] Implement `pilot/specfoundry_pilot/audit.py`:
  - AU01–AU11 exactly as in contracts/evidence-record.md, reading only files in the run dir
  - the redaction scan over the whole run dir (patterns plus `grep -rF -f <(cut -d= -f2- <secret env>)` for each secret env file present on the host; skip with a recorded note if absent)
  - write `audit.jsonl`; return the pass/fail count
- [X] T059 [US3] Wire `pilot audit [--run ID]` in `cli.py` (default: latest run dir; exit 0 only if all pass), and replace the `audit_pending` placeholder in `pipeline.resume` with `audit.run()`; a failing audit makes the run `failed(AUDIT)`, exit 1

**Checkpoint**: The US3 independent test passes on the synthetic evidence and on a real run's committed record.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T060 [P] Write `docs/harnesses.md`. Name no specific internal or private provider:
  - the harness options — OpenCode (used now, v2.2.7, how the pilot packages the host binary), Claude Code, Codex, GitHub Copilot CLI (later; what each needs: binary, key variable, headless flag, JSON output for spend)
  - how to configure a provider for OpenCode generically: `PILOT_MODEL` format `provider/model`, `OPENCODE_CONFIG_CONTENT` for any OpenAI-compatible endpoint with `{env:PILOT_MODEL_API_KEY}`, setting `PILOT_MODEL_EGRESS_HOSTS`, and when to set `PILOT_PROVIDER_CAP_DECLARED`
  - the spend-cap layers from R2
- [X] T061 [P] Write `pilot/README.md`: what the pilot proves, prerequisites, the four commands, where evidence lands, and links to quickstart.md and contracts
- [X] T062 Run the full quickstart.md end to end on this machine (steps 1–5), including the optional negative checks (`resume` before merge → exit 4; `N` at reconcile → exit 5; `N` at the retry prompt → exit 6, then `resume` re-asks; `run` with an open `pilot/*` PR → exit 2). Commit `specs/002-m1-gated-pilot/evidence/<run-id>/`
- [X] T063 Mutation test (as 001 T007): on a kept cluster, delete the worker NetworkPolicies in a test attempt namespace and confirm P06/P07 flip to fail; temporarily mount `scm-token` into a worker manifest copy and confirm P04/P09 fail. Record the result in `evidence/<run-id>/mutation.md`
- [X] T064 Update `specs/002-m1-gated-pilot/spec.md` (add an Evidence section linking the run summary) and `specs/002-m1-gated-pilot/plan.md` (known limits confirmed or changed). Do **not** edit the roadmap status; propose `002 → implemented/verified` via `/speckit-roadmap-debrief` and `/speckit-spec-status-reconcile` after review

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. T004 needs network and Docker.
- **Foundational (Phase 2)**: depends on Phase 1. Blocks all stories.
- **US1 (Phase 3)**: depends on Phase 2 (only `config.py`, `evidence.py` and `cli.py`; it needs no cluster).
- **US2 (Phase 4)**: depends on Phase 2 and on US1's `gate.py`, `fixture.py` and fixture template (T017–T022). The pipeline gates every step.
- **US3 (Phase 5)**: the audit (T051–T053, T058–T059) depends only on the evidence layout (T008) and can be built alongside US2. The live checks (T054–T057) hook into `worker.py`/`pipeline.py` (T041, T047).
- **Polish (Phase 6)**: depends on all stories. T062 is the acceptance run.

### Key task dependencies

- T004 → T027, T031, T032 (base digests)
- T017 → T014 (status captures) → T015 → T019
- T027 → T028 → T029 → T030 → T033
- T031 + T038 + T039 → T033
- T034–T037 → T041–T043, T049
- T040 → T041, T042, T043
- T041 + T042 + T043 + T044 + T045 + T046 → T047 → T048
- T055 → T041 (called from it). Implement a no-op `run_worker_checks` stub in T041 if US3 is later.
- T058 → T059 → T048 audit step

### Parallel Opportunities

- Phase 1: T003, T005, T006 together.
- Phase 2: T007, T008, T009 together (separate files).
- US1: T014–T016 tests together; T018 alongside T019.
- US2: tests T023–T026 together; images T027, T031, T032 together; manifests T034–T037 together.
- US3: T051–T053 together, and alongside US2 implementation.
- Polish: T060, T061 together.

---

## Parallel Example: User Story 2

```bash
# Tests first, together:
Task: "Write pilot/tests/test_frame.py"            # T023
Task: "Write pilot/tests/test_prompt.py"           # T024
Task: "Write pilot/tests/test_reconcile.py"        # T025
Task: "Write pilot/tests/test_publisher_idempotency.py"  # T026

# Then images and manifests, together:
Task: "Create pilot/images/worker/Dockerfile"      # T027
Task: "Create pilot/images/tools/Dockerfile"       # T031
Task: "Create pilot/images/egress/Dockerfile"      # T032
Task: "Create pilot/manifests/{egress,worker,grader,publisher}.yaml.tmpl"  # T034–T037
```

---

## Implementation Strategy

### MVP first (US1)

1. Phases 1–2, then Phase 3.
2. **Validate**: the gate matrix passes, and `pilot gate A/B --root pilot/fixture` behaves (allow / refuse with `DEP_UNSATISFIED:001`). This proves the product's core promise with no cluster or spend.

### Incremental delivery

1. US1 → the gate is proven fail-closed.
2. US2 → one full pilot with real PRs (it needs the throwaway repo, the publisher token and the `opencode/` credential directory; at most about $6 of spend).
3. US3 → audit and live checks; re-run the pilot to produce a fully audited record (T062).

### Operator prerequisites before US2 (not tasks — operator actions)

- Create the empty `<owner>/<name>-pilot-fixture` repo.
- Create a fine-grained token for it (contents and pull requests: write) in `~/.config/specfoundry/publisher.env`.
- Fill in `~/.config/specfoundry/pilot.env`, `publisher.env` (`chmod 600`) and `~/.config/specfoundry/opencode/` (`chmod 700`; `opencode.json` + `<provider>_api_key`, `chmod 600`).

---

## Notes

- [P] = different files, no dependencies on incomplete tasks.
- Never print, log or commit a secret value. Secret env files are passed by path only.
- No code path may call a GitHub merge endpoint (grep check is part of T062 review).
- Commit after each phase checkpoint.

---

## Implementation notes (2026-11-13)

Where the implementation differs from the wording of a task:

- **T035/T037 (manifests):** split into separate templates instead of `${UNIT}` switches:
  - `worker-ns`, `worker-job` and `worker-probe`
  - `grader` and `grader-job`
  - `publisher-ns` and `publisher-job`
  - plus `infra` (control pod and grader stand-in)
- **T038/T039 (grader, publisher):** written in Python (`pilot/images/tools/grade.py`,
  `publish.py`, stdlib only) instead of `grade.sh`/`publish.sh`. The publisher's logic can
  then be unit-tested (T026).
- **T051 (synthetic evidence):** built by `pilot/tests/evidence_builder.py` rather than a
  static fixture directory.
- **Worker credentials (T007, T041):** `model.env` is replaced by the `opencode/` directory:
  - it holds `opencode.json` with a `{file:...}` reference, plus `<provider>_api_key`
  - it is mounted read-only as the worker's `~/.config/opencode`
  - this is the only mechanism that authenticated with OpenCode 2.2.7 (contracts/config.md)
- **Induction (T030, T041):** the harness runs in a history-free workspace, and for A/1 the
  workspace `spec.md` is trimmed too. Without this, the model read the acceptance details
  from the repo (research R6).
- **Publisher identity (T043):** a fine-grained token belongs to a user, so AU03 checks
  PR author == `publisher_identity` (the token's login, from `GET /user`) rather than
  author ≠ operator.
- **Base revision per task:** each task builds on the commit its allowing gate decision
  evaluated (`input.fixture_commit`). So B builds on A's merged and verified code (FR-019).
