#!/usr/bin/env bash
# Worker entrypoint (contracts/worker-io.md). fd 3 = real stdout, reserved for the result frame;
# everything else (including all harness output) goes to files under /tmp.
set -uo pipefail
exec 3>&1
exec 1>>/tmp/entry.log 2>&1
LIB=/usr/local/lib/pilot
OUT=/tmp/out
mkdir -p "$OUT"
ERROR=""
HEXIT=""

meta() { python3 -c 'import json,sys; print(json.load(open("/in/meta.json"))[sys.argv[1]])' "$1"; }

finish() {
  cd /tmp || true
  python3 - "$ERROR" "$HEXIT" <<'PY' > "$OUT/report.json"
import json, os, re, subprocess, sys
meta = json.load(open("/in/meta.json"))
err, hexit = sys.argv[1] or None, sys.argv[2]
spend = json.load(open("/tmp/spend.json")) if os.path.exists("/tmp/spend.json") else None
def git(*a):
    r = subprocess.run(["git", "-C", "/tmp/.pilot/repo", *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""
head = git("rev-parse", "HEAD") or None
changed = [p for p in git("diff", "--name-only", meta["base_revision"], "HEAD").splitlines() if p] if head else []
tail = ""
for f in ("/tmp/entry.log", "/tmp/harness.stderr", "/tmp/harness.jsonl"):
    if os.path.exists(f):
        tail += open(f, errors="replace").read()[-2048:]
tail = re.sub(r"(sk-|ghp_|gho_|github_pat_)[A-Za-z0-9_\-]{4,}", r"\1***", tail)
tail = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}", r"\1***", tail)
print(json.dumps({
    "version": 1, "run_id": meta["run_id"], "task": meta["task"], "attempt": meta["attempt"],
    "base_revision": meta["base_revision"], "head": head,
    "harness": {"name": "opencode", "version": "2.2.7", "exit": int(hexit) if hexit not in ("", None) else None},
    "spend": spend, "changed_paths": changed, "error": err, "log_tail": tail[-4096:],
}))
PY
  args=("report.json=$OUT/report.json")
  [ -s "$OUT/change.bundle" ] && args+=("change.bundle=$OUT/change.bundle")
  python3 "$LIB/frame.py" emit "${args[@]}" >&3
  exit 0
}

BASE="$(meta base_revision)" || { ERROR="bad_meta"; finish; }
TASK="$(meta task)"; ATTEMPT="$(meta attempt)"
# The git checkout lives outside the harness's workspace; the harness works in /work/task, a plain
# copy without history. For an induced attempt (R6) the workspace spec also has the withheld
# section removed, so the harness cannot read it from the repo either.
REPO=/tmp/.pilot/repo
mkdir -p /tmp/.pilot /work/task
git clone --quiet /in/base.bundle "$REPO" || { ERROR="clone_failed"; finish; }
cd "$REPO"
git checkout --quiet "$BASE" || { ERROR="checkout_failed"; finish; }
git config user.name "pilot-worker"
git config user.email "pilot-worker@invalid"
git archive HEAD | tar -x -C /work/task || { ERROR="workspace_failed"; finish; }
python3 - <<'PY' || { ERROR="induction_failed"; finish; }
import json
m = json.load(open("/in/meta.json"))
ind = m.get("induction")
if ind:
    p = "/work/task/" + ind["spec_path"]
    s = open(p).read()
    i = s.index(ind["heading"])
    j = s.find("\n## ", i + len(ind["heading"]))
    s = s[:i] + (s[j + 1:] if j >= 0 else "")
    open(p, "w").write(s)
PY
cd /work/task

mkfifo /tmp/events
opencode run --standalone --format json --auto --model "$PILOT_MODEL" "$(cat /in/prompt.md)" \
  > /tmp/events 2> /tmp/harness.stderr &
HPID=$!
python3 "$LIB/watchdog.py" "$HPID" < /tmp/events
wait "$HPID"; HEXIT=$?
if python3 -c 'import json,sys; sys.exit(0 if json.load(open("/tmp/spend.json"))["stopped_by_cap"] else 1)'; then
  ERROR="spend_cap"
elif [ "$HEXIT" -ne 0 ]; then
  ERROR="harness_error"
fi

# Copy the workspace back over the checkout (deletions included), then restore the original
# spec: the induction's removal is not the worker's change.
cd "$REPO"
git ls-files -z | xargs -0 rm -f
cp -a /work/task/. "$REPO"/
SPEC_PATH="$(python3 -c 'import json; m=json.load(open("/in/meta.json")); print((m.get("induction") or {}).get("spec_path") or "")')"
[ -n "$SPEC_PATH" ] && git checkout --quiet HEAD -- "$SPEC_PATH"
git add -A
git commit --quiet -m "pilot: task $TASK attempt $ATTEMPT" || true
if [ "$(git rev-parse HEAD)" != "$BASE" ]; then
  git bundle create "$OUT/change.bundle" "$BASE..HEAD" || ERROR="${ERROR:-bundle_failed}"
fi
finish
