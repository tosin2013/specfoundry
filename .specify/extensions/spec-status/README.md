# spec-status extension v0.2.0

**Agent skills that turn `spec status` output into next actions.** This [Spec Kit](https://github.com/github/spec-kit) extension adds five skills to your AI coding agent (Claude Code, Cursor, Codex, Copilot and the others Spec Kit supports). They read your roadmap through the read-only [`spec status`](https://github.com/tosin2013/spec-status) CLI, explain what it found, catch records that disagree with each other, and help you fix them. Every change is proposed and needs your approval.

- [Why use it](#why-use-it)
- [Requirements](#requirements)
- [Install, upgrade, remove](#install-upgrade-remove)
- [The five skills](#the-five-skills)
- [Roles: pm, developer, qa, architect](#roles)
- [How changes are made (approval)](#how-changes-are-made)
- [Partner extensions](#partner-extensions)
- [Walkthroughs](#walkthroughs)
- [Troubleshooting](#troubleshooting)
- [Limits](#limits)
- [How it is built and tested](#how-it-is-built-and-tested)

## Why use it

`spec status` tells you what your roadmap and task files **record**: statuses, checked tasks, blockers and broken references. It does not tell you what to do about them, and some problems are not diagnostics at all. For example, an item recorded `implemented` with two of its three tasks unchecked produces a clean report:

```
001  implemented  active      Import data
  explain: checked tasks 1/3 in specs/001-import/tasks.md
  explain: unchecked checkbox at specs/001-import/tasks.md:4
  explain: unchecked checkbox at specs/001-import/tasks.md:5

diagnostics  none
```

The `reconcile` skill flags that disagreement, asks which side is wrong (is the work unfinished, or are the boxes stale?), and proposes the fix with the command that applies it. The other skills do the same job for blockers, superseded dependencies, unfamiliar diagnostics, and "can we call this verified yet?".

The skills never change a file on their own, never treat `verified` as proof, and never redirect a dependency on a superseded item without asking you.

## Requirements

| Needed | Version | Notes |
|---|---|---|
| Spec Kit (`specify`) | 1.2.0 or newer | Installs the extension and renders the skills for your agent |
| `spec` CLI | v0.1.2 or newer, on your `PATH` | [Install steps](https://github.com/tosin2013/spec-status#install). Every skill checks `spec version` first and stops with install instructions if it is missing |
| A Spec Kit roadmap | `.specify/memory/roadmap.md` | Written by the [speckit-roadmap](https://github.com/srobroek/speckit-roadmap) extension (`/speckit.roadmap.write`) or by hand in the same format |
| speckit-roadmap extension | recommended | Approved status, dependency and supersession changes go through `/speckit.roadmap.write`. Without it, the skills show you the exact edit to make by hand |

## Install, upgrade, remove

From a release (v0.2.0 or later). Replace `<version>`:

```sh
specify extension add spec-status --from https://github.com/tosin2013/spec-status/releases/download/v<version>/spec-status-extension_<version>.zip
```

From a clone of this repository, for example to try an unreleased change:

```sh
specify extension add --dev /path/to/spec-status/extensions/spec-status
```

`--dev` copies the folder at install time, so after changing it, run the command again with `--force`.

Check that it worked: your agent's skill list should show five `speckit-spec-status-*` skills, and `specify extension list` should list `spec-status`.

- **Upgrade:** run the `add` command again with the new version and `--force`.
- **Remove:** `specify extension remove spec-status`. Nothing else in your project changes.

The extension also registers one **optional** hook. After `/speckit-implement`, Spec Kit offers to run `reconcile`, and you can decline.

## The five skills

Start with **review**. It routes every finding to the skill that can deal with it.

| Skill | Use it when | What you get | What it may change |
|---|---|---|---|
| `/speckit.spec-status.review [as <role>] [focus]` | You want to know where the roadmap stands | Progress (recorded verified, checked tasks), blockers, human-review dependencies, diagnostics by severity, what is ready to start, and a primary next skill for every finding | Nothing |
| `/speckit.spec-status.reconcile [item]` | A status and its tasks or files disagree | Each mismatch with evidence (`path:line`), which side is likely wrong, and one proposed fix at a time with the command that applies it | Only what you approve, through the named command, then re-checked |
| `/speckit.spec-status.explain [SS_CODE \| item]` | A diagnostic code is unfamiliar | Meaning, severity, when it is fatal, typical cause, the fixing command, and where it occurs in your project | Nothing |
| `/speckit.spec-status.unblock [item]` | Work is blocked | Blockers in the order to clear them (depended-on items first), what each needs to reach `verified`, and a question for each superseded dependency | Dependency or supersession edits you approve, through `/speckit.roadmap.write` |
| `/speckit.spec-status.verify-readiness [item]` | You are about to record an item `verified` | A consistency check covering tasks, dependencies, error diagnostics and spec files, with every gap and its fix | Nothing. It never records a status |

**What reconcile detects:**
- **Tasks all checked, status early:** every task is checked but the status is `planned`, `specced` or `in-progress`.
- **Status ahead of tasks:** `implemented` or `verified` with unchecked tasks.
- **Status ahead of files:** `implemented` or `verified` with no task file, or a missing spec, plan or tasks file.
- **Unverified dependency:** `verified` while a dependency is not.
- **Unknown status word:** for example `done`. It suggests the highest status the evidence supports, never `verified`.
- **Missing link target:** a checked task links to a file that is missing.

## Roles

`review` can take a role. The role changes **what comes first** and which skills it recommends first. It never changes the facts: every role sees the same counts, findings and citations.

| Role | Leads with | Recommends first |
|---|---|---|
| (none) | progress, blockers, human review, diagnostics, ready to start | reconcile, unblock |
| `as pm` | progress, blockers, ready to start | unblock, reconcile |
| `as developer` | ready to start, unchecked tasks, missing spec/plan/tasks | reconcile, `/speckit-tasks`, `/speckit-implement` |
| `as qa` | evidence gaps: `implemented`/`verified` items with unchecked tasks, unread task files, unverified dependencies or errors | verify-readiness, `/speckit.roadmap.debrief`, `/speckit-analyze` |
| `as architect` | dependency chains, supersession, human review, governing constraints | unblock, explain, `/speckit.roadmap.sync` |

Example: `/speckit.spec-status.review as qa`. The full definitions are in [reference/roles.md](reference/roles.md).

## How changes are made

Every skill follows the same protocol ([reference/rules.md](reference/rules.md)), one change at a time:

1. **Propose:** the item, the evidence (`path:line`), the exact change, and the command that will make it.
2. **Wait** for your explicit yes to **this** change. A yes to an earlier change, text inside your roadmap or tasks, or a request from another agent is not approval.
3. **Apply.** Changes go through the named Spec Kit command:
   - `/speckit.roadmap.write` for status, dependency and supersession changes;
   - `/speckit-specify`, `/speckit-plan` or `/speckit-tasks` for missing files;
   - `/speckit-implement` for unfinished work.

   Some changes have no command, such as fixing a link or a checkbox in `tasks.md`. For those, the skill shows the exact before and after, and makes the edit only after you approve.
4. **Confirm:** the skill runs `spec status` again and reports **confirmed** (the finding is gone) or **unconfirmed** (it is still there, so it stops).

Decline, and nothing changes. The proposal stays "proposed".

## Partner extensions

If your project has these Spec Kit extensions installed, the matching role recommends their commands too. Installation is detected from `.specify/extensions/.registry`. A partner is never required, installed or run without your approval. If one is not installed, the role mentions it once with its install command.

| Role | Partner | What it adds | Notes |
|---|---|---|---|
| developer | **Bug Triage** (`bug`) | Assess, fix and test work reported broken | Default catalog: `specify extension add bug` |
| qa | **Assure** (`assure`) | Test-readiness analysis and a QA test manual as evidence before `verified` | Community catalog, not vetted by Spec Kit. Needs the `illustrate` extension and Python 3.11+ |
| architect | **Architecture Governance** (`arch-governance`) | Read-only check that specs and plans still cite current ADRs, plus an implementation gate | Community catalog, not vetted by Spec Kit. Its commands run Python scripts with `uv` (Python 3.11+) and call `git`. Its `install`, `sync`, `repin` and `issues` commands write files |

Review a community extension yourself before installing it. Exact versions and commands are in [reference/roles.md](reference/roles.md).

## Walkthroughs

These describe how the skills handle the example projects in [`testdata/skills/`](https://github.com/tosin2013/spec-status/tree/main/testdata/skills) of this repository. The facts come from real `spec status` output; the skill steps are paraphrased.

**1. Status ahead of tasks** (`implemented-unchecked`). Item 001 "Import data" is `implemented`, but `specs/001-import/tasks.md` has 1 of 3 tasks checked; lines 4 and 5 are unchecked. `spec status` reports no diagnostics.
1. `reconcile` reports a "status ahead of tasks" mismatch, citing the roadmap line and the two unchecked boxes.
2. It asks which is true: the work is unfinished, so lower 001 to `in-progress` via `/speckit.roadmap.write`; or the boxes are stale, so finish or tick the tasks via `/speckit-implement`.
3. Nothing changes until you choose. Then it applies your choice and re-runs `spec status`.

**2. A superseded dependency** (`superseded-dependency`). Item 003 depends on 001, which was superseded by 002.
1. `spec status` reports `SS_DEPENDENCY_HUMAN_REVIEW`, and `spec` never redirects the dependency itself.
2. `unblock` explains this and asks whether 003 should depend on 002 instead. Only after your yes does it change 003's `Depends on` via `/speckit.roadmap.write`, then confirm.

**3. Before marking verified** (`verified-dep-unverified`). Item 001 is `verified`, but its dependency 002 is only `planned`, which raises `SS_VERIFIED_DEPENDENCY_CONTRADICTION`.
1. `review as qa` lists 001 under evidence gaps.
2. `verify-readiness` reports "not consistent: dependency 002 is not verified", and points to `unblock` for 002 or to lowering 001's status.
3. It never records a status itself.

**4. The same roadmap through four roles** (`roles-mixed`). The facts are identical in every view: 2 of 7 active items recorded verified, 2 blocked, 1 human-review dependency.
- `as pm` leads with progress and what is ready to start (005, 007).
- `as developer` leads with ready work and unchecked tasks, and notes that 003 has every task checked but is still `planned`.
- `as qa` leads with 002: recorded `verified` with 1 of 2 tasks checked.
- `as architect` leads with the dependency chain 004 → 005 and the supersession 006 → 007.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| A skill says `spec` is not installed | Install the CLI ([steps](https://github.com/tosin2013/spec-status#install)) and make sure it is on the `PATH` your agent uses |
| `spec status` exits 2 (`SS_ROADMAP_UNAVAILABLE`) | The project has no `.specify/memory/roadmap.md`. Create one with `/speckit.roadmap.write`. The skills never create it for you |
| The report shows zero items | The roadmap is empty, or not in the supported format; `spec` cannot tell which. See the [supported input](https://github.com/tosin2013/spec-status#what-it-reads) |
| Roadmap changes are shown as manual edits | The speckit-roadmap extension is not installed. Install it, or make the shown edit yourself |
| No partner recommendations | The partner is not installed or is disabled. Check `specify extension list` |
| A skill warns about `schema_version` | Your `spec` prints a JSON schema other than 1.0. Update this extension to match your `spec` |
| A finding looks wrong in `spec` itself (a crash, a wrong count, a false warning) | The skills help you file a bug with the [issue form](https://github.com/tosin2013/spec-status/issues/new/choose). Security problems go to [private reporting](https://github.com/tosin2013/spec-status/security/advisories/new) |

## Limits

- **They are instructions, not code.** How faithfully a skill is followed depends on the agent and model. The checks below test structure and fixtures, not every agent.
- **No `argument-hint` in 1.2.0.** Spec Kit 1.2.0 does not carry `argument-hint` into extension skills, so the role names are written in `review`'s description. Type `as qa` and so on after the command.
- **Only what `spec` reports.** The skills know only what `spec status` reports, plus the files it names. They do not judge whether code is correct, and a consistent record is not proof.
- **Partner details can go stale.** The partner versions and commands in `roles.md` were checked on 2026-11-12. A partner that changes its commands is recommended only by what your registry actually lists.

## How it is built and tested

The extension is part of [spec-status](https://github.com/tosin2013/spec-status) (feature 005, `specs/005-agent-skills/`):
- **Repository tests** (`internal/extension`) check that the reference matches `spec`'s diagnostic and JSON contracts, that all five commands exist with the required sections, that every command link points to a real command, that roles and partners are well formed, and that the 12 example projects still produce the signals they expect.
- **Install check:** `scripts/check-extension-install.sh` installs the extension into a throwaway project and checks that exactly five skills appear.
- **Agent runs:** before release, an agent ran the installed skills on every example project without approving any change. The facts matched, and no file was modified.

Release archives carry a SHA-256 checksum. The extension version always equals the spec-status release version.

## License

Apache-2.0 ([LICENSE](LICENSE)).
