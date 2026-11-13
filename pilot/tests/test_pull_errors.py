"""Fail closed on image pull errors, naming the image (003 T015)."""
import unittest
from unittest import mock

from specfoundry_pilot import infra, k8s

PODS = {"items": [{"metadata": {"name": "proxy-1"}, "status": {"containerStatuses": [
    {"image": "ghcr.io/o/specfoundry-pilot-egress@sha256:" + "c" * 64,
     "state": {"waiting": {"reason": "ImagePullBackOff"}}}]}}]}


class TestPullErrors(unittest.TestCase):
    def test_detects_backoff(self):
        with mock.patch.object(k8s, "get_json", return_value=PODS):
            errs = k8s.pull_errors("ns")
        self.assertEqual(len(errs), 1)
        self.assertIn("ImagePullBackOff", errs[0])
        self.assertIn("@sha256:", errs[0])

    def test_fail_on_pull_names_image(self):
        with mock.patch.object(k8s, "get_json", return_value=PODS):
            with self.assertRaises(RuntimeError) as c:
                infra.fail_on_pull("ns", "egress not ready")
        self.assertIn("specfoundry-pilot-egress@sha256:", str(c.exception))
        self.assertIn("no local-build fallback", str(c.exception))

    def test_other_failure_still_raises(self):
        with mock.patch.object(k8s, "get_json", return_value={"items": []}):
            with self.assertRaises(RuntimeError) as c:
                infra.fail_on_pull("ns", "pod not ready")
        self.assertEqual(str(c.exception), "pod not ready")


if __name__ == "__main__":
    unittest.main()
