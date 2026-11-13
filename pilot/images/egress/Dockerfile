# Domain-allowlisting egress proxy (research R4). Non-root.
ARG ALPINE_BASE
FROM ${ALPINE_BASE}
RUN apk add --no-cache tinyproxy=1.11.2-r0 && adduser -D -H -u 10003 proxy && ! command -v sudo
USER 10003:10003
ENTRYPOINT ["tinyproxy", "-d", "-c", "/etc/pilot-proxy/tinyproxy.conf"]
