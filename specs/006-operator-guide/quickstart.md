# Quickstart: validate 006

## 1. Docs check (any machine)

```sh
PYTHONPATH=pilot python3 -m unittest pilot.tests.test_docs_check -v
python3 pilot/tools/docs_check.py          # expect exit 0
```

Negative check: put `pilot/pilot run --bogus` in a scratch copy of the guide. Expect exit 1
naming the line.

## 2. Review against the outline

Walk [contracts/guide-outline.md](contracts/guide-outline.md) section by section. Every row's
"Check" holds. Every edge case in the spec has a troubleshooting entry (SC-003).

## 3. Fresh-machine validation (the owner; SC-001, SC-002)

1. Provision Ubuntu 24.04 LTS amd64 (4+ CPU, 8 GB free RAM, 30 GB disk) with **none** of:
   specfoundry, kind, `~/.config/specfoundry`, `~/.config/opencode`.
2. Open `docs/operator-guide.md` on GitHub (the public repo) and follow **only** it. Keep
   `specs/006-operator-guide/evidence/validation-log.md` as you go:
   - section, start time, duration;
   - every hesitation, deviation or outside lookup.
3. Expected: the audit passes 11/11, teardown 3/3, and 2 draft PRs exist on your fixture
   repo (one merged by you).
4. For each log finding, fix the guide (each fix in its own commit), then re-check the
   affected sections.
5. Commit the run's evidence and the log under `specs/006-operator-guide/evidence/`.
6. Locally run `grep -rniF '<your-provider-host>' docs/ specs/006-operator-guide/`, using
   your real model host. Expect no output (SC-006).

## 4. Troubleshooting spot checks (SC-003)

On the validation machine, deliberately trigger and fix, using only `docs/troubleshooting.md`:
- a tag-only image reference;
- a wrong CNI hash;
- running `pilot/pilot run` without a terminal;
- leaving a pilot PR open before `run`;
- `resume` before merging.

Record each in the validation log.
