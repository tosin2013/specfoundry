# Grader + publisher image (C-09): spec from the verified upstream release. Non-root, no sudo,
# no secrets; runs under an arbitrary UID with group 0.
ARG DEBIAN_BASE

FROM ${DEBIAN_BASE} AS fetch
ARG SPEC_REPO
ARG SPEC_TAG
ARG SPEC_ASSET
ARG SPEC_ASSET_SHA256
ARG SPEC_SHA256
ARG SPEC_CHECKSUMS
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl=7.88.1-10+deb12u15 ca-certificates=20250419~deb12u2 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /fetch
RUN set -eu; base="https://github.com/${SPEC_REPO}/releases/download/${SPEC_TAG}"; \
    curl -fsSLO "${base}/${SPEC_ASSET}"; curl -fsSLO "${base}/${SPEC_CHECKSUMS}"; \
    grep " ${SPEC_ASSET}\$" "${SPEC_CHECKSUMS}" | sha256sum -c -; \
    echo "${SPEC_ASSET_SHA256}  ${SPEC_ASSET}" | sha256sum -c -; \
    tar -xzf "${SPEC_ASSET}"; cp */spec ./spec; \
    echo "${SPEC_SHA256}  spec" | sha256sum -c -

FROM ${DEBIAN_BASE}
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git=1:2.39.5-0+deb12u3 ca-certificates=20250419~deb12u2 python3=3.11.2-1+b1 \
      python3-pytest=7.2.1-2 curl=7.88.1-10+deb12u15 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10002 --gid 0 --create-home --home-dir /home/tools --shell /usr/sbin/nologin tools \
 && chgrp -R 0 /home/tools && chmod -R g=u /home/tools \
 && ! command -v sudo
COPY --from=fetch /fetch/spec /usr/local/bin/spec
COPY grade.py publish.py check_token.py frame.py /usr/local/lib/pilot/
RUN chmod 0755 /usr/local/bin/spec
ENV HOME=/home/tools PYTHONDONTWRITEBYTECODE=1
USER 10002:0
WORKDIR /tmp
