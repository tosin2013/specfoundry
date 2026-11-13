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
FEATURE_DIR = ROOT / "specs" / "002-m1-gated-pilot"
EVIDENCE_ROOT = FEATURE_DIR / "evidence"
UP_OK = BUILD / "up.ok"
IMAGES_JSON = BUILD / "images.json"
FIXTURE_BASE = BUILD / "fixture-base.txt"

CLUSTER = "specfoundry-m1"
CONTEXT = f"kind-{CLUSTER}"
REGISTRY_NAME = "specfoundry-registry"
REGISTRY_HOST = "localhost:5001"

# Fixture roadmap items behind the pilot's task labels.
TASKS = {"A": "001", "B": "002"}
SPEC_DIRS = {"A": "specs/001-slugify", "B": "specs/002-unique-slug"}


def read_pins() -> dict:
    out = {}
    for line in PINS.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out
