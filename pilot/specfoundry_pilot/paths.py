"""Well-known paths for the pilot (all absolute)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "pilot"
BUILD = PILOT / ".build"
FIXTURE_TEMPLATE = PILOT / "fixture"
GRADING = PILOT / "grading"
MANIFESTS = PILOT / "manifests"
IMAGES = PILOT / "images"
PINS = PILOT / "pins.env"
IMAGES_LOCK = PILOT / "images.lock"
DEFAULT_FEATURE_DIR = ROOT / "specs" / "002-m1-gated-pilot"


RUNS_DIR = ROOT / "pilot" / "runs"  # git-ignored; operators' runs when no feature is active


def feature_dir() -> Path:
    """The Spec Kit feature whose evidence folder receives runs: `PILOT_EVIDENCE_FEATURE` (a specs/
    path), else the active feature in `.specify/feature.json` (set by /speckit-specify). Returns
    DEFAULT_FEATURE_DIR only for callers that need a feature; see evidence_root()."""
    import json
    import os
    override = os.environ.get("PILOT_EVIDENCE_FEATURE")
    if override:
        return (ROOT / override).resolve()
    fj = ROOT / ".specify" / "feature.json"
    try:
        d = ROOT / json.loads(fj.read_text())["feature_directory"]
        if d.is_dir():
            return d
    except (OSError, ValueError, KeyError):
        pass
    return DEFAULT_FEATURE_DIR


def evidence_root() -> Path:
    """Where run evidence goes (analysis H2):
    - `PILOT_EVIDENCE_FEATURE` set            -> <that spec>/evidence   (maintainers)
    - an active feature in .specify/feature.json -> <feature>/evidence  (maintainers)
    - otherwise                                 -> pilot/runs/          (operators; git-ignored)
    so a newcomer's runs never land inside another spec's committed evidence."""
    import json
    import os
    if os.environ.get("PILOT_EVIDENCE_FEATURE"):
        return feature_dir() / "evidence"
    try:
        d = ROOT / json.loads((ROOT / ".specify" / "feature.json").read_text())["feature_directory"]
        if d.is_dir():
            return d / "evidence"
    except (OSError, ValueError, KeyError):
        pass
    return RUNS_DIR


FEATURE_DIR = feature_dir()
EVIDENCE_ROOT = evidence_root()
UP_OK = BUILD / "up.ok"
IMAGES_JSON = BUILD / "images.json"
IMAGE_SOURCE = BUILD / "image-source.txt"
FIXTURE_BASE = BUILD / "fixture-base.txt"
MODEL_HOST = BUILD / "model-host.txt"  # git-ignored; the provider host never goes into evidence

CLUSTER = "specfoundry-m1"
CONTEXT = f"kind-{CLUSTER}"
REGISTRY_NAME = "specfoundry-registry"
REGISTRY_HOST = "localhost:5001"

# Fixture roadmap items behind the pilot's task labels.
TASKS = {"A": "001", "B": "002"}
SPEC_DIRS = {"A": "specs/001-slugify", "B": "specs/002-unique-slug"}


def _read_env(path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def read_pins() -> dict:
    return _read_env(PINS)


def read_lock() -> dict:
    """Image digests written by the pilot-images workflow (pilot/images.lock)."""
    return _read_env(IMAGES_LOCK)
