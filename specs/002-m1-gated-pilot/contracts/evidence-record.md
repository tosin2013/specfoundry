# Contract: evidence record

Root: `specs/002-m1-gated-pilot/evidence/<run-id>/`. `<run-id>` = `YYYYMMDDTHHMMSSZ`
(UTC). Everything is committed. Nothing in it may contain a secret, and the redaction
scan (R12) fails the run if anything does.

```text
<run-id>/
├── run.json                    # resumable state (data-model: Run)
├── events.jsonl                # ordered: {seq, at, stage, task, attempt, event, detail}
├── versions.txt                # kind, kubectl, server, node image, calico sha, image digests, opencode sha, spec version
├── config.json                 # pilot.env values (non-secret) + sha256 of each secret env file
├── gate/<seq>-<task>.json      # decision (gate-decision.schema.json)
├── gate/<seq>-<task>.status.json   # raw spec status --json
├── attempts/<task>-<n>/
│   ├── prompt.md               # exact prompt given to the worker
│   ├── meta.json               # exact /in/meta.json
│   ├── induction.json          # only when induced: {name, removed_heading, removed_sha256, removed_bytes}
│   ├── change.bundle           # worker output (kept for grading audit and publish resume)
│   ├── manifests.yaml          # rendered (Secret data omitted)
│   ├── report.json             # worker-io.md
│   ├── grade.json              # grade-report.schema.json
│   ├── proxy-denials.log       # model-egress denials during the attempt
│   └── job.json                # final Job/pod status (reason, exit, times)
├── prs.json
├── reconcile/<task>.json
├── checks/results.jsonl        # live isolation/credential checks (IDs P01…)
├── audit.jsonl                 # evidence-only audit (IDs AU01…)
├── teardown.jsonl              # T01…
└── summary.md                  # human summary: order of events, PR links, pass/fail counts
```

## Required live checks (`checks/results.jsonl`)

Run against every worker attempt, grader and the publisher while they exist.

| ID | Req | Check |
|---|---|---|
| P01 | FR-005 | worker namespace has exactly 1 pod, 1 container |
| P02 | FR-006 | SA and pod `automountServiceAccountToken=false`; no token file |
| P03 | FR-006 | default-deny netpol present; quota has pods=1, count/secrets=1; Job has activeDeadlineSeconds |
| P04 | FR-007 | the worker's only Secret is `model-key`; no env var name matches SCM patterns |
| P05 | FR-007 | no grading ConfigMap or volume exists in the worker namespace |
| P06 | FR-009b | the worker can reach the model host via the proxy (control) and cannot reach `github.com` via the proxy or directly |
| P07 | FR-010 | worker → grader namespace blocked; control → grader reachable |
| P08 | FR-010 | worker SA `can-i` create/patch in the grader namespace = no |
| P09 | FR-013 | only `pilot-publish` holds an SCM Secret (scan all namespaces) |
| P10 | S6 | every pilot pod image is `@sha256:`, non-root, no privilege escalation |

## Required audit checks (`audit.jsonl`, from files only)

| ID | Check |
|---|---|
| AU01 | every refusal of B came before A's `verified` event; no attempt for B before it (SC-001) |
| AU02 | order A/1 fail → A/2 pass → B pass is present in `events.jsonl` (SC-002) |
| AU03 | `prs.json` has exactly 2 entries (one per task), both draft, and each PR's author equals `publisher_identity` (the login of the publisher token, read by the publisher Job via `GET /user`) (SC-003) |
| AU04 | every P04/P09 row passed for every unit (SC-004) |
| AU05 | the gate fail-closed matrix rows all passed (SC-005) |
| AU06 | every attempt's `spend.cost_usd ≤ cap_usd` or `stopped_by_cap` (SC-008) |
| AU07 | the teardown rows all passed (SC-006) |
| AU08 | the redaction scan is clean |
| AU09 | every attempt with n>1 is preceded in `events.jsonl` by a `retry_confirmed` event for the same task and n |
| AU10 | a `mode_confirmed` event exists and comes before the first attempt event |
| AU11 | A/1 has `induction.json` and its `prompt.md` has no `## Acceptance details`; every other attempt has no `induction.json` and its prompt contains that section; the sha256 of the A/1 removed span equals the sha256 of that section in A/2's prompt |
