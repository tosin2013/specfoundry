"""Digest-only image references from pilot/images.lock (003 T004, FR-005, data-model)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from specfoundry_pilot import images, paths

D = "a" * 64
GOOD = {
    "IMAGE_REGISTRY": "ghcr.io/tosin2013",
    "WORKER_IMAGE": f"ghcr.io/tosin2013/specfoundry-pilot-worker@sha256:{D}",
    "TOOLS_IMAGE": f"ghcr.io/tosin2013/specfoundry-pilot-tools@sha256:{D}",
    "EGRESS_IMAGE": f"ghcr.io/tosin2013/specfoundry-pilot-egress@sha256:{D}",
}


class TestValidateRef(unittest.TestCase):
    def test_accepts_digest(self):
        images.validate_ref(GOOD["WORKER_IMAGE"])
        images.validate_ref(f"localhost:5001/pilot-worker@sha256:{D}")

    def test_rejects(self):
        for bad in ("ghcr.io/x/y:latest", "ghcr.io/x/y:sha-abc", "", f"ghcr.io/x/y@sha256:{'A' * 64}",
                    f"ghcr.io/x/y@sha256:{'a' * 63}", f"ghcr.io/x/y:tag@sha256:{D}"):
            with self.subTest(bad), self.assertRaises(images.ImageRefError):
                images.validate_ref(bad)


class TestLoadPinned(unittest.TestCase):
    def test_ok(self):
        r = images.load_pinned(GOOD)
        self.assertEqual(set(r), {"worker", "tools", "egress"})
        self.assertEqual(r["worker"], GOOD["WORKER_IMAGE"])

    def test_bad_key_named(self):
        for key in ("WORKER_IMAGE", "TOOLS_IMAGE", "EGRESS_IMAGE"):
            with self.subTest(key):
                lock = dict(GOOD, **{key: "ghcr.io/x/y:latest"})
                with self.assertRaises(images.ImageRefError) as c:
                    images.load_pinned(lock)
                self.assertIn(key, str(c.exception))

    def test_empty_placeholder_rejected(self):
        with self.assertRaises(images.ImageRefError):
            images.load_pinned(dict(GOOD, TOOLS_IMAGE=""))


class TestReadLock(unittest.TestCase):
    def test_read_lock_verbatim(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "images.lock"
            p.write_text("# c\nWORKER_IMAGE=" + GOOD["WORKER_IMAGE"] + "\n")
            with mock.patch.object(paths, "IMAGES_LOCK", p):
                self.assertEqual(paths.read_lock()["WORKER_IMAGE"], GOOD["WORKER_IMAGE"])

    def test_missing_lock_is_image_ref_error(self):
        with mock.patch.object(paths, "IMAGES_LOCK", Path("/nonexistent/images.lock")):
            with self.assertRaises(images.ImageRefError):
                images.read_lock()

    def test_pins_values_verbatim(self):
        pins = paths.read_pins()
        self.assertRegex(pins["OPENCODE_ASSET_SHA256"], r"^[0-9a-f]{64}$")
        self.assertRegex(pins["CALICO_SHA256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()


class TestFeatureDir(unittest.TestCase):
    def test_override_env(self):
        with mock.patch.dict("os.environ", {"PILOT_EVIDENCE_FEATURE": "specs/002-m1-gated-pilot"}):
            self.assertEqual(paths.feature_dir().name, "002-m1-gated-pilot")

    def test_feature_json_used_when_valid(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / ".specify").mkdir()
            (root / "specs" / "009-x").mkdir(parents=True)
            (root / ".specify" / "feature.json").write_text('{"feature_directory": "specs/009-x"}')
            with mock.patch.object(paths, "ROOT", root), mock.patch.dict("os.environ", {}, clear=False):
                import os
                os.environ.pop("PILOT_EVIDENCE_FEATURE", None)
                self.assertEqual(paths.feature_dir(), root / "specs" / "009-x")

    def test_fallback_when_missing(self):
        with tempfile.TemporaryDirectory() as t, mock.patch.object(paths, "ROOT", Path(t)):
            import os
            os.environ.pop("PILOT_EVIDENCE_FEATURE", None)
            self.assertEqual(paths.feature_dir(), paths.DEFAULT_FEATURE_DIR)
