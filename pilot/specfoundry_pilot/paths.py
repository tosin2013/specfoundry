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
FEATURE_DIR = ROOT / "specs" / "002-m1-gated-pilot"
EVIDENCE_ROOT = FEATURE_DIR / "evidence"
UP_OK = BUILD / "up.ok"
IMAGES_JSON = BUILD / "images.json"
IMAGE_SOURCE = BUILD / "image-source.txt"
FIXTURE_BASE = BUILD / "fixture-base.txt"

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
