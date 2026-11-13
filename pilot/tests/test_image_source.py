"""Image source selection: pinned digests by default, local build only on request (003 T007)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from specfoundry_pilot import cluster, evidence, images, paths

D = "b" * 64
LOCK = {"WORKER_IMAGE": f"ghcr.io/o/specfoundry-pilot-worker@sha256:{D}",
        "TOOLS_IMAGE": f"ghcr.io/o/specfoundry-pilot-tools@sha256:{D}",
        "EGRESS_IMAGE": f"ghcr.io/o/specfoundry-pilot-egress@sha256:{D}"}


class TestUpImageSource(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        b = Path(self.tmp.name)
        self.patches = [mock.patch.object(paths, "BUILD", b), mock.patch.object(paths, "UP_OK", b / "up.ok"),
                        mock.patch.object(paths, "IMAGES_JSON", b / "images.json"),
                        mock.patch.object(paths, "IMAGE_SOURCE", b / "image-source.txt")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def run_up(self, local_build):
        cfg = mock.Mock()
        with mock.patch.object(cluster, "up_cluster") as upc, \
             mock.patch("specfoundry_pilot.publisher_token.verify", return_value={"ok": True}), \
             mock.patch("specfoundry_pilot.publisher_token.report"), \
             mock.patch.object(images, "read_lock", return_value=LOCK), \
             mock.patch.object(images, "build_all", return_value={"worker": "w", "tools": "t", "egress": "e"}) as ba, \
             mock.patch("specfoundry_pilot.infra.apply_all") as ap:
            cluster.up(cfg, local_build=local_build)
        return upc, ba, ap

    def test_default_pulls_pinned_never_builds(self):
        upc, ba, ap = self.run_up(False)
        upc.assert_called_once_with(local_build=False)
        ba.assert_not_called()
        imgs = ap.call_args[0][1]
        self.assertEqual(imgs["worker"], LOCK["WORKER_IMAGE"])
        self.assertEqual(paths.IMAGE_SOURCE.read_text().strip(), "pinned")
        self.assertEqual(json.loads(paths.IMAGES_JSON.read_text())["worker"], LOCK["WORKER_IMAGE"])

    def test_local_build_builds(self):
        upc, ba, ap = self.run_up(True)
        upc.assert_called_once_with(local_build=True)
        ba.assert_called_once()
        self.assertEqual(paths.IMAGE_SOURCE.read_text().strip(), "local-build")


class TestVersionsRecordsSource(unittest.TestCase):
    def test_versions_txt(self):
        with tempfile.TemporaryDirectory() as t:
            b = Path(t)
            (b / "image-source.txt").write_text("pinned\n")
            run = mock.Mock()
            run.id, run.dir = "r1", b
            with mock.patch.object(paths, "BUILD", b), mock.patch.object(paths, "IMAGE_SOURCE", b / "image-source.txt"), \
                 mock.patch.object(evidence, "_cmd", return_value="x"):
                evidence.write_versions(run, {"worker": LOCK["WORKER_IMAGE"]})
            txt = (b / "versions.txt").read_text()
            self.assertIn("image_source: pinned", txt)
            self.assertIn("image_worker: " + LOCK["WORKER_IMAGE"], txt)


if __name__ == "__main__":
    unittest.main()
