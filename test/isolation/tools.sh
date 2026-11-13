#!/usr/bin/env bash
# Install pinned kind and kubectl into ~/.local/bin, verifying published checksums.
set -euo pipefail
KIND_VERSION="${KIND_VERSION:-v0.27.0}"
KUBECTL_VERSION="${KUBECTL_VERSION:-v1.32.2}"
BIN="${BIN:-$HOME/.local/bin}"
ARCH=amd64; case "$(uname -m)" in aarch64|arm64) ARCH=arm64;; esac
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
mkdir -p "$BIN"; tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

if ! "$BIN/kind" version 2>/dev/null | grep -q "$KIND_VERSION"; then
  u="https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-${OS}-${ARCH}"
  curl -fsSL -o "$tmp/kind" "$u"
  want="$(curl -fsSL "$u.sha256sum" | awk '{print $1}')"
  echo "$want  $tmp/kind" | sha256sum -c -
  install -m 0755 "$tmp/kind" "$BIN/kind"
fi
if ! "$BIN/kubectl" version --client 2>/dev/null | grep -q "$KUBECTL_VERSION"; then
  u="https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/${OS}/${ARCH}/kubectl"
  curl -fsSL -o "$tmp/kubectl" "$u"
  echo "$(curl -fsSL "$u.sha256")  $tmp/kubectl" | sha256sum -c -
  install -m 0755 "$tmp/kubectl" "$BIN/kubectl"
fi
"$BIN/kind" version
"$BIN/kubectl" version --client | head -1
