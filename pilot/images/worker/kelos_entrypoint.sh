#!/usr/bin/env bash
# Compatibility shim for Kelos's agent-image contract (/kelos_entrypoint.sh, prompt as $1).
# specfoundry does not depend on Kelos (constitution VI, C-05); this only lets teams that run
# Kelos use the hardened specfoundry worker image. The pilot reads its prompt from /in.
exec /usr/local/lib/pilot/entrypoint.sh "$@"
