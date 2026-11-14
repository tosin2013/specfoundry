"""`pilot publisher-token` keeps only a token that passes the scope check (finding F3)."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from specfoundry_pilot import publisher_token


def fake_prompt(token):
    def write(path):
        path.write_text(f"PILOT_SCM_TOKEN={token}\n")
        path.chmod(0o600)
        return 0
    return write


class TestRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = Path(self.tmp.name) / "publisher.env"
        self.cfg = SimpleNamespace(publisher_env=self.env, repo="owner/x-pilot-fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, token, ok):
        with mock.patch.object(publisher_token, "write_from_prompt", fake_prompt(token)), \
             mock.patch.object(publisher_token, "verify", return_value={"ok": ok}) as v, \
             mock.patch.object(publisher_token, "report"):
            rc = publisher_token.run(self.cfg)
        self.assertEqual(v.call_args.args[1], publisher_token.staging_path(self.cfg))
        return rc

    def test_failing_token_not_saved_previous_kept(self):
        self.env.write_text("PILOT_SCM_TOKEN=old\n")
        self.assertEqual(self.run_with("broad", ok=False), 1)
        self.assertEqual(self.env.read_text(), "PILOT_SCM_TOKEN=old\n")
        self.assertFalse(publisher_token.staging_path(self.cfg).exists())

    def test_failing_token_not_saved_when_none_before(self):
        self.assertEqual(self.run_with("broad", ok=False), 1)
        self.assertFalse(self.env.exists())
        self.assertFalse(publisher_token.staging_path(self.cfg).exists())

    def test_passing_token_replaces_previous(self):
        self.env.write_text("PILOT_SCM_TOKEN=old\n")
        self.assertEqual(self.run_with("scoped", ok=True), 0)
        self.assertEqual(self.env.read_text(), "PILOT_SCM_TOKEN=scoped\n")
        self.assertEqual(self.env.stat().st_mode & 0o777, 0o600)
        self.assertFalse(publisher_token.staging_path(self.cfg).exists())


if __name__ == "__main__":
    unittest.main()
