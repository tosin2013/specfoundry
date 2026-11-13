"""Redaction scan (T051, R12): patterns plus exact secret values from files, by path only."""
import tempfile
import unittest
from pathlib import Path

from specfoundry_pilot import audit


class TestRedaction(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ev = self.root / "ev"
        self.ev.mkdir()
        (self.ev / "ok.txt").write_text("pilot-w-a-1 task-a ask-me sk-short\n")
        self.keyfile = self.root / "p_api_key"
        self.keyfile.write_text("Zq9-unusual-secret-value-123")
        self.envfile = self.root / "publisher.env"
        self.envfile.write_text("# c\nPILOT_SCM_TOKEN=abcdEFGH1234-token-value\n")

    def tearDown(self):
        self.tmp.cleanup()

    def scan(self):
        return audit.redaction_scan(self.ev, key_files=[self.keyfile], env_files=[self.envfile])

    def test_clean(self):
        self.assertEqual(self.scan(), [])

    def test_patterns(self):
        # assembled at runtime so no token-shaped literal sits in the source
        body = "abcdefghijklmnopqrstuvwxyz12"
        for s in ("github" + "_pat_11" + body, "gh" + "p_" + body, "gh" + "o_" + body,
                  "s" + "k-" + body, "Authorization: Bear" + "er " + body):
            with self.subTest(s):
                (self.ev / "leak.txt").write_text(f"x {s} y\n")
                self.assertTrue(self.scan())

    def test_exact_values(self):
        (self.ev / "leak.txt").write_text("...Zq9-unusual-secret-value-123...")
        self.assertTrue(self.scan())
        (self.ev / "leak.txt").write_text("abcdEFGH1234-token-value")
        self.assertTrue(self.scan())

    def test_sha256_of_secret_file_is_not_a_leak(self):
        import hashlib
        (self.ev / "config.json").write_text(hashlib.sha256(self.keyfile.read_bytes()).hexdigest())
        self.assertEqual(self.scan(), [])


if __name__ == "__main__":
    unittest.main()
