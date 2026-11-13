# Thin worker image (C-09): OpenCode from the verified upstream release, never an operator's
# local binary. Non-root, no sudo, no secrets; runs under an arbitrary UID with group 0
# (OpenShift restricted SCC friendly).
ARG DEBIAN_BASE

FROM ${DEBIAN_BASE} AS fetch
ARG OPENCODE_REPO
ARG OPENCODE_TAG
ARG OPENCODE_ASSET
ARG OPENCODE_ASSET_SHA256
ARG OPENCODE_SHA256
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl=7.88.1-10+deb12u15 ca-certificates=20250419~deb12u2 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /fetch
RUN set -eu; base="https://github.com/${OPENCODE_REPO}/releases/download/${OPENCODE_TAG}"; \
    curl -fsSLO "${base}/${OPENCODE_ASSET}"; curl -fsSLO "${base}/SHA256SUMS"; \
    grep " ${OPENCODE_ASSET}\$" SHA256SUMS | sha256sum -c -; \
    echo "${OPENCODE_ASSET_SHA256}  ${OPENCODE_ASSET}" | sha256sum -c -; \
    tar -xzf "${OPENCODE_ASSET}"; \
    echo "${OPENCODE_SHA256}  opencode" | sha256sum -c -

FROM ${DEBIAN_BASE}
# Exact versions resolved 2026-11-13 with `apt-cache policy` on the pinned base.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git=1:2.39.5-0+deb12u3 ca-certificates=20250419~deb12u2 python3=3.11.2-1+b1 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --gid 0 --create-home --home-dir /home/worker --shell /usr/sbin/nologin worker \
 && mkdir -p /work /home/worker/.config \
 && chgrp -R 0 /home/worker /work && chmod -R g=u /home/worker /work \
 && ! command -v sudo
COPY --from=fetch /fetch/opencode /usr/local/bin/opencode
COPY entrypoint.sh watchdog.py frame.py /usr/local/lib/pilot/
# Kelos-compatible entrypoint shim (FR-010): lets Kelos users run this hardened image.
# It adds no dependency on Kelos.
COPY kelos_entrypoint.sh /kelos_entrypoint.sh
RUN chmod 0755 /usr/local/bin/opencode /usr/local/lib/pilot/entrypoint.sh /kelos_entrypoint.sh
ENV HOME=/home/worker PYTHONDONTWRITEBYTECODE=1 \
    OPENCODE_DISABLE_AUTOUPDATE=1 \
    OPENCODE_DISABLE_MODELS_FETCH=1 \
    OPENCODE_DISABLE_FREE_MODELS=1 \
    OPENCODE_DISABLE_CLAUDE_CODE=1
USER 10001:0
WORKDIR /work
ENTRYPOINT ["/usr/local/lib/pilot/entrypoint.sh"]
