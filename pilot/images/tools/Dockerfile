# Grader + publisher image: git, python3, pytest, curl, spec (sha256-verified). Non-root, no sudo.
ARG DEBIAN_BASE
FROM ${DEBIAN_BASE}
ARG SPEC_SHA256
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git=1:2.39.5-0+deb12u3 ca-certificates=20250419~deb12u2 python3=3.11.2-1+b1 \
      python3-pytest=7.2.1-2 curl=7.88.1-10+deb12u15 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10002 --create-home --home-dir /home/tools --shell /usr/sbin/nologin tools \
 && ! command -v sudo
COPY spec /usr/local/bin/spec
RUN echo "${SPEC_SHA256}  /usr/local/bin/spec" | sha256sum -c - && chmod 0755 /usr/local/bin/spec
COPY grade.py publish.py check_token.py frame.py /usr/local/lib/pilot/
ENV HOME=/home/tools PYTHONDONTWRITEBYTECODE=1
USER 10002:10002
WORKDIR /tmp
