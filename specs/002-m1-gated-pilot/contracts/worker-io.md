# Contract: worker inputs and outputs

## Inputs (all read-only mounts in the worker pod)

| Path | Source | Content |
|---|---|---|
| `/in/base.bundle` | ConfigMap `inputs` | `git bundle` of the fixture at `base_revision` |
| `/in/prompt.md` | ConfigMap `inputs` | Task prompt built from the fixture spec, plus tasks for that task. For A/1, the "Acceptance details" section is left out (R6) |
| `/in/meta.json` | ConfigMap `inputs` | `{run_id, task, attempt, base_revision, allowed_paths[], spend_cap_usd, token_cap}` |
| env from Secret `model-key` | Secret | `PILOT_MODEL_API_KEY` (and optional `OPENCODE_CONFIG_CONTENT`) |
| env | pod spec | `HTTPS_PROXY=http://proxy.pilot-egress-model.svc:8888`, `PILOT_MODEL` |

Writable only: `/work`, `/home/worker` and `/tmp` (emptyDir, size-limited).

## Behaviour

1. Clone `/in/base.bundle` into `/work/repo`, with git identity `pilot-worker`.
2. Run `opencode run --format json --auto --model "$PILOT_MODEL"` with the prompt. The
   harness output goes to `/tmp/harness.jsonl`, never to stdout.
3. A watchdog applies the spend cap (R2).
4. Commit all changes in one commit on top of `base_revision`.
5. Write `change.bundle` (`base_revision..HEAD`) and `report.json`, tar them, and
   print the frame.

## Output frame (stdout; nothing else from the entrypoint goes to stdout)

```text
PILOT-RESULT-BEGIN v1
<base64 of tar{change.bundle, report.json}>
PILOT-RESULT-END sha256=<hex of the decoded tar>
```

The orchestrator rejects a frame that is missing, doubled or bigger than 512 KiB
decoded, or whose sha256 doesn't match. Any of those makes the attempt `failed`.

## `report.json`

```json
{
  "version": 1,
  "run_id": "…", "task": "A", "attempt": 1,
  "base_revision": "<sha>", "head": "<sha>",
  "harness": {"name": "opencode", "version": "2.2.7", "exit": 0},
  "spend": {"cap_usd": 1.0, "cap_mode": "cost", "cost_usd": 0.12, "tokens": 48211, "stopped_by_cap": false},
  "changed_paths": ["src/…", "specs/001-…/tasks.md"],
  "log_tail": "<last 4 KiB of harness log, redacted>"
}
```
