#!/usr/bin/env bash
# Arbitrary-UID smoke test for the pilot images (003 US2, T023/T024).
# Runs each image as UID 1000123 / GID 0 with a read-only root filesystem and only the same
# writable mounts the pods get. Used by .github/workflows/pilot-images.yml before pushing, and
# locally. Needs: docker, git, python3.
#
#   WORKER=<ref> TOOLS=<ref> EGRESS=<ref> pilot/images/smoke.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
UID_ARB=1000123
W="$(mktemp -d)"; trap 'docker rm -f pilot-smoke-proxy >/dev/null 2>&1 || true; docker network rm pilot-smoke >/dev/null 2>&1 || true; rm -rf "$W"' EXIT
RUN=(docker run --rm --user "${UID_ARB}:0" --read-only --security-opt no-new-privileges --cap-drop ALL)
frame() { PYTHONPATH="$ROOT/pilot" python3 -c '
import sys, json
from specfoundry_pilot import frame
files, err = frame.decode(sys.stdin.read(), required=(sys.argv[1],))
if err: sys.exit(f"bad frame: {err}")
print(json.dumps(json.loads(files[sys.argv[1]]))[:400])' "$1"; }
fail=0

# --- fixture repo + bundles --------------------------------------------------------------
mkdir -p "$W/repo" "$W/in" "$W/grade" "$W/grading" "$W/proxy"
cp -r "$ROOT/pilot/fixture/." "$W/repo/"
git -C "$W/repo" init -q -b main
git -C "$W/repo" add -A
git -C "$W/repo" -c user.name=smoke -c user.email=smoke@invalid commit -qm base
BASE="$(git -C "$W/repo" rev-parse HEAD)"
git -C "$W/repo" bundle create -q "$W/in/base.bundle" HEAD
cp "$W/in/base.bundle" "$W/grade/base.bundle"
cp "$ROOT/pilot/tests/reference/slugkit/slug.py" "$W/repo/src/slugkit/slug.py"
echo 'from .slug import slugify  # noqa: F401' >> "$W/repo/src/slugkit/__init__.py"
sed -i 's/- \[ \]/- [X]/' "$W/repo/specs/001-slugify/tasks.md"
git -C "$W/repo" add -A
git -C "$W/repo" -c user.name=smoke -c user.email=smoke@invalid commit -qm solution
git -C "$W/repo" bundle create -q "$W/grade/change.bundle" "$BASE..HEAD"
cp "$ROOT/pilot/grading/"*.py "$W/grading/"
META='{"run_id":"smoke","task":"A","attempt":1,"item_id":"001","base_revision":"'"$BASE"'","allowed_paths":["src/slugkit/*","tests/*","specs/001-slugify/tasks.md"],"induction":null}'
echo "$META" > "$W/in/meta.json"; echo "$META" > "$W/grade/meta.json"
echo "Reply with ok." > "$W/in/prompt.md"
chmod -R a+rX "$W"

# --- worker: starts, runs its pipeline, emits a frame (no model config -> harness error) --
echo "== worker ($WORKER) as uid $UID_ARB"
if out="$("${RUN[@]}" --tmpfs /tmp:exec,mode=1777 --tmpfs /work:mode=1777 --tmpfs /home/worker:mode=1777 \
      -v "$W/in:/in:ro" -e PILOT_MODEL=none/none "$WORKER" | frame report.json)"; then
  echo "  PASS frame decoded: $out"
else echo "  FAIL worker produced no valid frame"; fail=1; fi

# --- tools: grades the reference solution, no network -------------------------------------
echo "== tools ($TOOLS) as uid $UID_ARB"
if out="$("${RUN[@]}" --network none --tmpfs /tmp:exec,mode=1777 -v "$W/grade:/in:ro" -v "$W/grading:/grading:ro" \
      "$TOOLS" python3 /usr/local/lib/pilot/grade.py | frame grade.json)" && echo "$out" | grep -q '"result": "pass"'; then
  echo "  PASS grade: pass"
else echo "  FAIL grader: $out"; fail=1; fi

# --- egress: tinyproxy starts and enforces the allowlist ----------------------------------
echo "== egress ($EGRESS) as uid $UID_ARB"
sed -n '1,200p' "$ROOT/pilot/images/egress/tinyproxy.conf.tmpl" > "$W/proxy/tinyproxy.conf"
printf '^allowed\\.invalid$\n' > "$W/proxy/allowlist"
chmod -R a+rX "$W/proxy"
docker network create pilot-smoke >/dev/null
docker run -d --name pilot-smoke-proxy --network pilot-smoke --user "${UID_ARB}:0" --read-only --cap-drop ALL \
  --tmpfs /tmp:mode=1777 -v "$W/proxy:/etc/pilot-proxy:ro" "$EGRESS" >/dev/null
sleep 2
code="$(docker run --rm --network pilot-smoke --user "${UID_ARB}:0" --read-only --tmpfs /tmp:mode=1777 "$TOOLS" \
  curl -s -o /dev/null -w '%{http_code}' --max-time 5 -x http://pilot-smoke-proxy:8888 https://blocked.invalid/ || true)"
if docker logs pilot-smoke-proxy 2>&1 | grep -q 'refused on filtered domain "blocked.invalid"'; then
  echo "  PASS proxy running and refused a non-allowlisted host (curl http=$code)"
else echo "  FAIL proxy did not refuse as expected"; docker logs pilot-smoke-proxy 2>&1 | tail -5; fail=1; fi

[ "$fail" -eq 0 ] && echo "== smoke: all images pass as an arbitrary UID" || { echo "== smoke: FAILED"; exit 1; }
