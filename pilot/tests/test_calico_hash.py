"""Calico manifest hash check before apply (003 T006, FR-007)."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from specfoundry_pilot import cluster


class TestVerifyCalico(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Path(self.tmp.name) / "calico.yaml"
        self.f.write_text("kind: Namespace\n")
        self.sha = hashlib.sha256(self.f.read_bytes()).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def test_match(self):
        cluster.verify_calico(self.f, self.sha)

    def test_mismatch_mentions_both(self):
        with self.assertRaises(RuntimeError) as c:
            cluster.verify_calico(self.f, "0" * 64)
        self.assertIn("0" * 64, str(c.exception))
        self.assertIn(self.sha, str(c.exception))

    def test_empty_expected(self):
        for exp in ("", None):
            with self.subTest(exp), self.assertRaises(RuntimeError):
                cluster.verify_calico(self.f, exp)


if __name__ == "__main__":
    unittest.main()
