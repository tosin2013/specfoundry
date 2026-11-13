# M0 isolation run 20261113T014128Z

**Result:** 37 of 37 checks pass.

| ID | Req | Result | Check |
|---|---|---|---|
| C01 | S4 | pass | Calico is the CNI and calico-node is ready |
| C02 | S4 | pass | kindnet (non-enforcing default CNI) is absent |
| C03 | FR-001 | pass | worker namespace runs exactly one pod |
| C04 | FR-001 | pass | worker pod has exactly one container |
| C05 | FR-001 | pass | a second pod in the worker namespace is rejected by quota |
| C06 | FR-002 | pass | service account has automountServiceAccountToken=false |
| C07 | FR-002 | pass | pod has automountServiceAccountToken=false |
| C08 | FR-002 | pass | no token file inside the worker container |
| C09 | FR-002 | pass | worker SA cannot read secrets in its own namespace |
| C10 | S5 | pass | worker SA cannot create pods in the grader namespace |
| C11 | S5 | pass | worker SA cannot exec or write in the grader namespace |
| C12 | FR-003 | pass | default-deny policy covers Ingress and Egress |
| C13 | FR-003 | pass | worker resolves cluster DNS (allowlisted) |
| C14 | FR-003 | pass | worker reaches the allowlisted target |
| C15 | FR-003 | pass | worker is blocked from the denied target |
| C16 | FR-003 | pass | control reaches the denied target (proves C15 is policy) |
| C17 | S5 | pass | worker is blocked from the grader |
| C18 | S5 | pass | control reaches the grader (proves C17 is policy) |
| C19 | FR-003 | pass | worker is blocked from the Kubernetes API |
| C20 | FR-003 | pass | control reaches the Kubernetes API (proves C19 is policy) |
| C21 | FR-003 | pass | worker is blocked from the internet |
| C22 | FR-003 | pass | control reaches the internet (proves C21 is policy) |
| C23 | FR-003 | pass | ingress to the worker is blocked |
| C24 | FR-003 | pass | worker is listening, so C23 is policy (loopback reach) |
| C25 | FR-004 | pass | ResourceQuota caps pods, cpu, memory and secrets |
| C26 | FR-004 | pass | worker pod has activeDeadlineSeconds |
| C27 | FR-004 | pass | a pod past its deadline is killed (DeadlineExceeded) |
| C28 | FR-005 | pass | no Secrets exist in the worker namespace |
| C29 | FR-005 | pass | creating a Secret in the worker namespace is rejected |
| C30 | FR-005 | pass | worker environment carries no credential-like variables |
| C31 | FR-005 | pass | worker pod mounts no Secret volumes |
| C32 | S6 | pass | worker runs as non-root (uid != 0) |
| C33 | S6 | pass | no privilege escalation, all capabilities dropped, read-only root fs |
| C34 | S6 | pass | no sudo in the worker image |
| C35 | S6 | pass | worker image is pinned by digest |
| T01 | N3 | pass | kind cluster deleted |
| T02 | N3 | pass | no kind node containers remain |
