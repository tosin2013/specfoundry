# Mutation test (T063), run 20261113T030655Z

Isolation was broken on purpose in a throwaway worker-policy namespace (`pilot-w-mut-1`, rendered from the
same `worker-ns.yaml.tmpl`) to show the live checks fail when the control they test is removed.

| Probe / check | With policies (expected) | Mutated | Mutated state |
|---|---|---|---|
| direct internet (P06) | blocked (http=000) | NetworkPolicies deleted | reachable (http=301) |
| github.com direct (P06) | blocked (http=000) | NetworkPolicies deleted | reachable (http=200) |
| grader stand-in (P07) | blocked (http=000) | NetworkPolicies deleted | reachable (http=200) |
| P09 only pilot-publish holds an SCM credential | pass | dummy `PILOT_SCM_TOKEN` Secret in `pilot-w-mut-1` | FAIL (caught): holders=['pilot-publish/scm-token', 'pilot-w-mut-1/model-key'] |
| P04 no SCM-like secret keys in the worker namespace | pass | same | FAIL (caught): keys=['PILOT_SCM_TOKEN'] |

**Result:** every mutation was caught. The `blocked` results in `checks/results.jsonl` therefore come from policy, not from the network, and the credential checks are not vacuous.
