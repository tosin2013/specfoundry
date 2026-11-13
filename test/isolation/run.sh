#!/usr/bin/env bash
# M0 stub isolation suite: one command stands up kind + Calico, runs the checks,
# writes evidence into the repo, tears down, and verifies the teardown.
#
#   test/isolation/run.sh            # full cycle (exit 0 only if every check passes)
#   KEEP=1 test/isolation/run.sh     # leave the cluster up for debugging
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"

CLUSTER=specfoundry-m0
CALICO_VERSION="${CALICO_VERSION:-v3.29.3}"
IMAGE="${IMAGE:-docker.io/library/busybox:1.36.1@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
EVID="${EVID:-$ROOT/specs/001-m0-isolation-stub/evidence/$RUN_ID}"
K="kubectl --context kind-$CLUSTER"
WORKER_SA="system:serviceaccount:m0-worker:worker"

mkdir -p "$EVID"
RESULTS="$EVID/results.jsonl"; : > "$RESULTS"
LOG="$EVID/run.log"; exec > >(tee -a "$LOG") 2>&1
PASS=0; FAIL=0

record() { # id requirement result description detail
  local id="$1" req="$2" res="$3" desc="$4" detail="${5:-}"
  if [ "$res" = pass ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
  printf '%-4s %-5s %-10s %s%s\n' "$(echo "$res" | tr a-z A-Z)" "$id" "$req" "$desc" "${detail:+ ($detail)}"
  python3 -c 'import json,sys; print(json.dumps(dict(zip(["id","requirement","result","description","detail"],sys.argv[1:]))))' \
    "$id" "$req" "$res" "$desc" "$detail" >> "$RESULTS"
}
check() { # id requirement description command...
  local id="$1" req="$2" desc="$3"; shift 3
  local out; if out="$("$@" 2>&1)"; then record "$id" "$req" pass "$desc" "$out"
  else record "$id" "$req" fail "$desc" "$out"; fi
}
# probe ns pod url -> prints "connected" or "blocked: <reason>"; exit 0 if connected
probe() {
  local out; out="$($K -n "$1" exec "$2" -- wget -q -T 4 -O /dev/null "$3" 2>&1)"; local rc=$?
  if [ $rc -eq 0 ] || echo "$out" | grep -q 'HTTP/'; then echo connected; return 0; fi
  echo "blocked: $(echo "$out" | tr '\n' ' ' | cut -c1-80)"; return 1
}
reach()   { probe "$@"; }
noreach() { if probe "$@" >/dev/null; then echo "unexpectedly connected"; return 1; fi; echo blocked; }
wexec()   { $K -n m0-worker exec worker -- "$@"; }
jp()      { $K "$@"; }

teardown() {
  echo "== teardown"
  kind delete cluster --name "$CLUSTER" >/dev/null 2>&1
  check T01 N3 "kind cluster deleted" bash -c "! kind get clusters 2>/dev/null | grep -qx $CLUSTER && echo absent"
  check T02 N3 "no kind node containers remain" bash -c \
    "n=\$(docker ps -a --filter label=io.x-k8s.kind.cluster=$CLUSTER -q | wc -l); echo containers=\$n; [ \$n -eq 0 ]"
}

echo "== run $RUN_ID evidence -> ${EVID#$ROOT/}"
"$HERE/tools.sh"
kind delete cluster --name "$CLUSTER" >/dev/null 2>&1 || true
kind create cluster --config "$HERE/kind-config.yaml" --wait 0s || { echo "cluster create failed"; exit 2; }

echo "== calico $CALICO_VERSION"
CALICO_URL="https://raw.githubusercontent.com/projectcalico/calico/$CALICO_VERSION/manifests/calico.yaml"
curl -fsSL "$CALICO_URL" -o "$EVID/calico.yaml" || { echo "calico download failed"; exit 2; }
$K apply -f "$EVID/calico.yaml" >/dev/null
$K -n kube-system rollout status ds/calico-node --timeout=300s
$K -n kube-system rollout status deploy/calico-kube-controllers --timeout=300s
$K wait --for=condition=Ready node --all --timeout=180s
$K -n kube-system rollout status deploy/coredns --timeout=180s

echo "== fixtures"
targets=""
for ns in m0-allowed m0-denied m0-grader; do
  targets+="---
apiVersion: v1
kind: Pod
metadata: {name: target, namespace: $ns, labels: {app: target}}
spec:
  restartPolicy: Never
  securityContext: {runAsNonRoot: true, runAsUser: 65534, seccompProfile: {type: RuntimeDefault}}
  containers:
    - name: target
      image: $IMAGE
      command: [sh, -c, \"mkdir -p /tmp/www && echo $ns > /tmp/www/index.html && httpd -f -p 8080 -h /tmp/www\"]
      securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: [ALL]}}
---
apiVersion: v1
kind: Service
metadata: {name: target, namespace: $ns}
spec:
  selector: {app: target}
  ports: [{port: 8080, targetPort: 8080}]
"
done
python3 - "$HERE/manifests.yaml" "$IMAGE" "$targets" > "$EVID/manifests.rendered.yaml" <<'PY'
import sys; s=open(sys.argv[1]).read()
print(s.replace("__IMAGE__", sys.argv[2]).replace("__TARGETS__", sys.argv[3]))
PY
$K apply -f "$EVID/manifests.rendered.yaml" >/dev/null
for p in m0-worker/worker m0-control/control m0-allowed/target m0-denied/target m0-grader/target; do
  $K -n "${p%/*}" wait --for=condition=Ready "pod/${p#*/}" --timeout=180s >/dev/null
done
WORKER_IP="$($K -n m0-worker get pod worker -o jsonpath='{.status.podIP}')"
API_IP="$($K get svc kubernetes -o jsonpath='{.spec.clusterIP}')"

echo "== checks"
# Cluster / CNI (C-06)
check C01 S4 "Calico is the CNI and calico-node is ready" bash -c \
  "$K -n kube-system get ds calico-node -o jsonpath='{.status.numberReady}/{.status.desiredNumberScheduled}' | grep -E '^([1-9][0-9]*)/\1$'"
check C02 S4 "kindnet (non-enforcing default CNI) is absent" bash -c \
  "! $K -n kube-system get ds kindnet >/dev/null 2>&1 && echo absent"

# FR-001 one worker per pod and namespace
check C03 FR-001 "worker namespace runs exactly one pod" bash -c \
  "n=\$($K -n m0-worker get pods --no-headers | wc -l); echo pods=\$n; [ \$n -eq 1 ]"
check C04 FR-001 "worker pod has exactly one container" bash -c \
  "n=\$($K -n m0-worker get pod worker -o jsonpath='{range .spec.containers[*]}{.name}{\"\\n\"}{end}' | grep -c .); echo containers=\$n; [ \$n -eq 1 ]"
check C05 FR-001 "a second pod in the worker namespace is rejected by quota" bash -c \
  "out=\$($K -n m0-worker run second --image=$IMAGE --restart=Never --command -- sleep 1 2>&1); \
   $K -n m0-worker delete pod second --ignore-not-found >/dev/null 2>&1; echo \"\$out\" | grep -qi 'exceeded quota' && echo rejected"

# FR-002 no service-account token
check C06 FR-002 "service account has automountServiceAccountToken=false" bash -c \
  "[ \"\$($K -n m0-worker get sa worker -o jsonpath='{.automountServiceAccountToken}')\" = false ] && echo false"
check C07 FR-002 "pod has automountServiceAccountToken=false" bash -c \
  "[ \"\$($K -n m0-worker get pod worker -o jsonpath='{.spec.automountServiceAccountToken}')\" = false ] && echo false"
check C08 FR-002 "no token file inside the worker container" bash -c \
  "$K -n m0-worker exec worker -- sh -c '! ls /var/run/secrets/kubernetes.io/serviceaccount/token 2>/dev/null' && echo absent"
check C09 FR-002 "worker SA cannot read secrets in its own namespace" bash -c \
  "[ \"\$($K auth can-i get secrets -n m0-worker --as=$WORKER_SA)\" = no ] && echo no"

# S5 grader isolation (RBAC)
check C10 S5 "worker SA cannot create pods in the grader namespace" bash -c \
  "[ \"\$($K auth can-i create pods -n m0-grader --as=$WORKER_SA)\" = no ] && echo no"
check C11 S5 "worker SA cannot exec or write in the grader namespace" bash -c \
  "a=\$($K auth can-i create pods/exec -n m0-grader --as=$WORKER_SA); b=\$($K auth can-i create configmaps -n m0-grader --as=$WORKER_SA); \
   echo exec=\$a configmaps=\$b; [ \$a = no ] && [ \$b = no ]"

# FR-003 network policy
check C12 FR-003 "default-deny policy covers Ingress and Egress" bash -c \
  "$K -n m0-worker get netpol default-deny-all -o jsonpath='{.spec.policyTypes}' | grep -q Ingress && \
   $K -n m0-worker get netpol default-deny-all -o jsonpath='{.spec.policyTypes}' | grep -q Egress && echo Ingress,Egress"
check C13 FR-003 "worker resolves cluster DNS (allowlisted)" \
  $K -n m0-worker exec worker -- nslookup target.m0-allowed.svc.cluster.local
check C14 FR-003 "worker reaches the allowlisted target" reach m0-worker worker http://target.m0-allowed.svc.cluster.local:8080/
check C15 FR-003 "worker is blocked from the denied target" noreach m0-worker worker http://target.m0-denied.svc.cluster.local:8080/
check C16 FR-003 "control reaches the denied target (proves C15 is policy)" reach m0-control control http://target.m0-denied.svc.cluster.local:8080/
check C17 S5 "worker is blocked from the grader" noreach m0-worker worker http://target.m0-grader.svc.cluster.local:8080/
check C18 S5 "control reaches the grader (proves C17 is policy)" reach m0-control control http://target.m0-grader.svc.cluster.local:8080/
check C19 FR-003 "worker is blocked from the Kubernetes API" noreach m0-worker worker "http://$API_IP:443/"
check C20 FR-003 "control reaches the Kubernetes API (proves C19 is policy)" reach m0-control control "http://$API_IP:443/"
check C21 FR-003 "worker is blocked from the internet" noreach m0-worker worker http://1.1.1.1/
check C22 FR-003 "control reaches the internet (proves C21 is policy)" reach m0-control control http://1.1.1.1/
check C23 FR-003 "ingress to the worker is blocked" noreach m0-control control "http://$WORKER_IP:8080/"
check C24 FR-003 "worker is listening, so C23 is policy (loopback reach)" \
  $K -n m0-worker exec worker -- wget -q -T 4 -O - http://127.0.0.1:8080/

# FR-004 quota and deadline
check C25 FR-004 "ResourceQuota caps pods, cpu, memory and secrets" bash -c \
  "$K -n m0-worker get resourcequota worker-quota -o jsonpath='{.spec.hard}' | tee /dev/stderr | \
   python3 -c 'import json,sys; h=json.load(sys.stdin); sys.exit(0 if all(k in h for k in [\"pods\",\"limits.cpu\",\"limits.memory\",\"count/secrets\"]) and h[\"pods\"]==\"1\" else 1)'"
check C26 FR-004 "worker pod has activeDeadlineSeconds" bash -c \
  "v=\$($K -n m0-worker get pod worker -o jsonpath='{.spec.activeDeadlineSeconds}'); echo \$v; [ -n \"\$v\" ]"
check C27 FR-004 "a pod past its deadline is killed (DeadlineExceeded)" bash -c \
  "for i in \$(seq 1 30); do r=\$($K -n m0-deadline get pod deadline -o jsonpath='{.status.reason}'); \
   [ \"\$r\" = DeadlineExceeded ] && { echo \$r; exit 0; }; sleep 3; done; echo reason=\$r; exit 1"

# FR-005 no credentials
check C28 FR-005 "no Secrets exist in the worker namespace" bash -c \
  "n=\$($K -n m0-worker get secrets --no-headers 2>/dev/null | wc -l); echo secrets=\$n; [ \$n -eq 0 ]"
check C29 FR-005 "creating a Secret in the worker namespace is rejected" bash -c \
  "out=\$($K -n m0-worker create secret generic gh --from-literal=token=x 2>&1); echo \"\$out\" | grep -qi 'exceeded quota' && echo rejected"
check C30 FR-005 "worker environment carries no credential-like variables" bash -c \
  "! $K -n m0-worker exec worker -- env | grep -iE 'TOKEN|GITHUB|^GH_|API_KEY|SECRET|PASSWORD' && echo none"
check C31 FR-005 "worker pod mounts no Secret volumes" bash -c \
  "! $K -n m0-worker get pod worker -o jsonpath='{.spec.volumes[*].secret}' | grep -q . && echo none"

# S6 image and runtime hardening
check C32 S6 "worker runs as non-root (uid != 0)" bash -c \
  "u=\$($K -n m0-worker exec worker -- id -u); echo uid=\$u; [ \"\$u\" != 0 ]"
check C33 S6 "no privilege escalation, all capabilities dropped, read-only root fs" bash -c \
  "s=\$($K -n m0-worker get pod worker -o jsonpath='{.spec.containers[0].securityContext}'); echo \$s; \
   echo \$s | grep -q '\"allowPrivilegeEscalation\":false' && echo \$s | grep -q '\"drop\":\[\"ALL\"\]' && echo \$s | grep -q '\"readOnlyRootFilesystem\":true'"
check C34 S6 "no sudo in the worker image" bash -c \
  "$K -n m0-worker exec worker -- sh -c '! command -v sudo' && echo absent"
check C35 S6 "worker image is pinned by digest" bash -c \
  "i=\$($K -n m0-worker get pod worker -o jsonpath='{.spec.containers[0].image}'); echo \$i; echo \$i | grep -q '@sha256:'"

# Versions for the evidence record
{
  echo "run_id: $RUN_ID"
  echo "kind: $(kind version)"
  echo "kubectl: $(kubectl version --client | head -1)"
  echo "server: $($K version -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)["serverVersion"]["gitVersion"])')"
  echo "node_image: $(docker inspect --format '{{.Config.Image}}' $CLUSTER-control-plane)"
  echo "calico: $CALICO_VERSION sha256=$(sha256sum "$EVID/calico.yaml" | cut -d' ' -f1)"
  echo "worker_image: $IMAGE"
  echo "host: $(uname -srm)"
} > "$EVID/versions.txt"
rm -f "$EVID/calico.yaml"  # large upstream file; its sha256 is recorded above

if [ "${KEEP:-0}" = 1 ]; then echo "KEEP=1: cluster left running"; else teardown; fi

TOTAL=$((PASS+FAIL))
python3 - "$RESULTS" "$EVID/summary.md" "$RUN_ID" <<'PY'
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1])]
p=sum(r["result"]=="pass" for r in rows)
with open(sys.argv[2],"w") as f:
    f.write(f"# M0 isolation run {sys.argv[3]}\n\n**Result:** {p} of {len(rows)} checks pass.\n\n")
    f.write("| ID | Req | Result | Check |\n|---|---|---|---|\n")
    for r in rows: f.write(f"| {r['id']} | {r['requirement']} | {r['result']} | {r['description']} |\n")
PY
echo "== result: $PASS of $TOTAL pass  evidence: ${EVID#$ROOT/}"
[ "$FAIL" -eq 0 ]
