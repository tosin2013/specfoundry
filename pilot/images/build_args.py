#!/usr/bin/env python3
"""Single source of image build arguments, from pilot/pins.env (used by `pilot up --local-build`
and by .github/workflows/pilot-images.yml).

    build_args.py <worker|tools|egress> [--format=docker|github]

docker: one `KEY=VALUE` per line (for --build-arg); github: `KEY=VALUE` lines for a multi-line
`build-args` input. Stdlib only.
"""
import sys
from pathlib import Path

PINS = Path(__file__).resolve().parents[1] / "pins.env"


def read_pins(path=PINS) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def split_release(ref: str) -> tuple[str, str]:
    repo, tag = ref.split("@", 1)
    return repo, tag


def build_args(image: str, pins: dict | None = None) -> dict:
    p = pins or read_pins()
    if image == "worker":
        repo, tag = split_release(p["OPENCODE_RELEASE"])
        return {"DEBIAN_BASE": p["DEBIAN_BASE"], "OPENCODE_REPO": repo, "OPENCODE_TAG": tag,
                "OPENCODE_ASSET": p["OPENCODE_ASSET"], "OPENCODE_ASSET_SHA256": p["OPENCODE_ASSET_SHA256"],
                "OPENCODE_SHA256": p["OPENCODE_SHA256"]}
    if image == "tools":
        repo, tag = split_release(p["SPEC_RELEASE"])
        version = tag.lstrip("v")
        return {"DEBIAN_BASE": p["DEBIAN_BASE"], "SPEC_REPO": repo, "SPEC_TAG": tag,
                "SPEC_ASSET": p["SPEC_ASSET"], "SPEC_ASSET_SHA256": p["SPEC_ASSET_SHA256"],
                "SPEC_SHA256": p["SPEC_SHA256"], "SPEC_CHECKSUMS": f"spec_{version}_checksums.txt"}
    if image == "egress":
        return {"ALPINE_BASE": p["ALPINE_BASE"]}
    raise SystemExit(f"unknown image {image!r}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for k, v in build_args(sys.argv[1]).items():
        print(f"{k}={v}")
