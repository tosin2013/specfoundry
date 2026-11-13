# Contract: image source (CLI deltas from 002)

| Command | Behaviour |
|---|---|
| `pilot up` | Default. Validate `WORKER_IMAGE`, `TOOLS_IMAGE` and `EGRESS_IMAGE` in `pilot/images.lock` as digest references (a missing file is an error). kind pulls them directly from the public registry (no local registry, no pull secret). Check `CALICO_SHA256` before applying Calico. Exit 2 on: a missing or tag-only reference, the registry unreachable (an image pull fails within the timeout), or a hash mismatch. Records `image_source: pinned` |
| `pilot up --local-build` | 002 behaviour: start the local registry, build from `pilot/images/`, push, and use those digests. Records `image_source: local-build` |

All other commands, prompts, exit codes and the evidence layout are unchanged from 002
(`specs/002-m1-gated-pilot/contracts/`). `versions.txt` adds `image_source:` and the three
digest references used.
