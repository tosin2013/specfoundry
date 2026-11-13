# Quickstart: validate 003

Commands and expected outcomes only. Design details are in [research.md](research.md) and
[contracts/](contracts/).

## 1. Images built in GitHub (US1)

```sh
gh workflow run pilot-images.yml        # or push a change under pilot/images/** to main
gh run watch                            # verify: SHA256SUMS check of opencode-linux-x64.tar.gz passes
gh pr list --head 'pilot-images/'       # digest PR; review and merge it
```

Expected:
- three public packages exist, `ghcr.io/tosin2013/specfoundry-pilot-{worker,tools,egress}`;
- `pilot/pins.env` holds `@sha256:` references after the merge;
- a PR touching `pilot/images/**` builds but does not push.

## 2. Enterprise readiness (US2)

For each image, run with an arbitrary UID and a read-only root filesystem:

```sh
docker run --rm --user 1000123:0 --read-only --tmpfs /tmp:exec,mode=1777 ... <image@digest>
```

Expected:
- the worker produces a frame;
- the grader grades a known-good bundle;
- the egress proxy starts.

Mirror check: `docker pull` by digest, re-tag to another registry, point the pins at it,
and `pilot up` works the same.

## 3. Pull-by-digest stand-up (FR-005, FR-007)

```sh
pilot/pilot up        # expect: no local registry; images pulled by digest; Calico hash OK
```

Negative checks, each exiting 2 before anything runs:
- a wrong `CALICO_SHA256`;
- a tag-only `WORKER_IMAGE`.

## 4. Validation pilot run on the GitHub-built images (SC-001, SC-002)

```sh
pilot/pilot reset-fixture && pilot/pilot run      # confirm mode, confirm retry
# merge A's draft PR on GitHub
pilot/pilot resume                                # approve reconcile
pilot/pilot down && pilot/pilot audit             # AU01–AU11 pass; versions.txt: image_source=pinned
```

## 5. Competitive review (US3)

Write `kelos-review.md` per
[contracts/competitive-review-template.md](contracts/competitive-review-template.md).

Expected:
- 8 of 8 security-bar rows for both products, each with a citation or "unverified";
- at least 5 capability rows;
- an attribution section;
- no Kelos components in any pilot cluster.
