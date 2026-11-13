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


def feature_dir() -> Path:
    """Evidence goes to the active Spec Kit feature (`.specify/feature.json`, set by
    /speckit-specify), else to 002's folder. `PILOT_EVIDENCE_FEATURE` (a specs/ path) overrides."""
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


FEATURE_DIR = feature_dir()
EVIDENCE_ROOT = FEATURE_DIR / "evidence"
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
