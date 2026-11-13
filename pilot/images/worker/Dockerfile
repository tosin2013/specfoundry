# Thin worker image: git + python3 + OpenCode (operator binary, sha256-verified). Non-root, no sudo.
ARG DEBIAN_BASE
FROM ${DEBIAN_BASE}
ARG OPENCODE_SHA256
# Exact versions resolved 2026-11-13 with `apt-cache policy` on the pinned base.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git=1:2.39.5-0+deb12u3 ca-certificates=20250419~deb12u2 python3=3.11.2-1+b1 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --create-home --home-dir /home/worker --shell /usr/sbin/nologin worker \
 && ! command -v sudo
COPY opencode /usr/local/bin/opencode
RUN echo "${OPENCODE_SHA256}  /usr/local/bin/opencode" | sha256sum -c - && chmod 0755 /usr/local/bin/opencode
COPY entrypoint.sh watchdog.py frame.py /usr/local/lib/pilot/
RUN chmod 0755 /usr/local/lib/pilot/entrypoint.sh
ENV HOME=/home/worker PYTHONDONTWRITEBYTECODE=1 \
    OPENCODE_DISABLE_AUTOUPDATE=1 \
    OPENCODE_DISABLE_MODELS_FETCH=1 \
    OPENCODE_DISABLE_FREE_MODELS=1 \
    OPENCODE_DISABLE_CLAUDE_CODE=1
USER 10001:10001
WORKDIR /work
ENTRYPOINT ["/usr/local/lib/pilot/entrypoint.sh"]
