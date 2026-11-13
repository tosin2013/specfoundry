"""Stdout result frame used by worker, grader and publisher pods (contracts/worker-io.md).

    PILOT-RESULT-BEGIN v1
    <base64 of a tar of named files>
    PILOT-RESULT-END sha256=<hex of the decoded tar>

Stdlib only: this file is also copied into the worker and tools images.
"""
from __future__ import annotations

import base64
import hashlib
import io
import sys
import tarfile

BEGIN = "PILOT-RESULT-BEGIN v1"
END_PREFIX = "PILOT-RESULT-END sha256="
MAX_BYTES = 512 * 1024


def encode(files: dict) -> str:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in sorted(files.items()):
            if isinstance(data, str):
                data = data.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))
    raw = buf.getvalue()
    b64 = base64.encodebytes(raw).decode()
    return f"{BEGIN}\n{b64}{END_PREFIX}{hashlib.sha256(raw).hexdigest()}\n"


def decode(log_text: str, required=("report.json",)):
    """Return (files: dict[str, bytes] | None, error: str | None).

    error is one of: no_result, bad_frame, oversize.
    """
    lines = (log_text or "").splitlines()
    begins = [i for i, l in enumerate(lines) if l.strip() == BEGIN]
    if not begins:
        return None, "no_result"
    if len(begins) > 1:
        return None, "bad_frame"
    start = begins[0]
    ends = [i for i in range(start + 1, len(lines)) if lines[i].startswith(END_PREFIX)]
    if len(ends) != 1:
        return None, "bad_frame"
    end = ends[0]
    want = lines[end][len(END_PREFIX):].strip()
    body = "".join(l.strip() for l in lines[start + 1:end])
    if len(body) > (MAX_BYTES * 4) // 3 + 16:
        return None, "oversize"
    try:
        raw = base64.b64decode(body, validate=True)
    except Exception:  # noqa: BLE001
        return None, "bad_frame"
    if len(raw) > MAX_BYTES:
        return None, "oversize"
    if hashlib.sha256(raw).hexdigest() != want:
        return None, "bad_frame"
    files = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
            for m in tar.getmembers():
                if not m.isfile() or "/" in m.name or m.name.startswith(".") or m.name in files:
                    return None, "bad_frame"
                files[m.name] = tar.extractfile(m).read()
    except Exception:  # noqa: BLE001
        return None, "bad_frame"
    for r in required:
        if r not in files:
            return None, "bad_frame"
    return files, None


def main(argv=None):
    """CLI for images: `frame.py emit name=path ...` prints a frame to stdout."""
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] != "emit":
        print("usage: frame.py emit name=path ...", file=sys.stderr)
        return 2
    files = {}
    for spec in argv[1:]:
        name, path = spec.split("=", 1)
        try:
            with open(path, "rb") as f:
                files[name] = f.read()
        except FileNotFoundError:
            continue
    sys.stdout.write(encode(files))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
