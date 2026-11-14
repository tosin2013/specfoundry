"""Operator config checks (contracts/config.md)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from specfoundry_pilot import config
from specfoundry_pilot.config import ConfigError

PILOT_ENV = """PILOT_FIXTURE_REPO=owner/foo-pilot-fixture
PILOT_FIXTURE_BRANCH=main
PILOT_MODEL=provider/model
PILOT_MODEL_EGRESS_HOSTS=api.example.com
"""


class TestRepoGuard(unittest.TestCase):
    def test_accepts_pilot_fixture(self):
        config.repo_guard("owner/foo-pilot-fixture", "tosin2013/specfoundry")

    def test_rejects(self):
        for repo, origin in [("owner/specfoundry", None), ("owner/specfoundry-test", None),
                             ("tosin2013/x-pilot-fixture", "tosin2013/x-pilot-fixture"), ("not a repo", None)]:
            with self.subTest(repo), self.assertRaises(ConfigError) as c:
                config.repo_guard(repo, origin)
            self.assertEqual(c.exception.code, 3)


class TestLoad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"SPECFOUNDRY_CONFIG": str(self.d)})
        self.env.start()
        self.write("pilot.env", PILOT_ENV)
        (self.d / "opencode").mkdir(mode=0o700)
        self.write("opencode/opencode.json",
                   '{"providers": {"p": {"settings": {"baseURL": "https://x", "apiKey": "{file:~/.config/opencode/p_api_key}"}}}}')
        self.write("opencode/p_api_key", "abc")
        self.write("opencode/opencode.json.bak.x", '{"apiKey": "sk-literal"}')
        self.write("publisher.env", "PILOT_SCM_TOKEN=xyz\n")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def write(self, name, text, mode=0o600):
        p = self.d / name
        p.write_text(text)
        p.chmod(mode)

    def test_ok(self):
        cfg = config.load(guard=False)
        self.assertEqual(cfg.retry_limit, 2)
        self.assertEqual(cfg.model_hosts, ["api.example.com"])
        self.assertEqual(cfg["PILOT_SPEND_CAP_USD"], "1.00")

    def test_missing_files_say_what_to_do(self):
        # 006 validation finding: a fresh machine ran publisher-token before pilot.env existed.
        (self.d / "pilot.env").unlink()
        with self.assertRaises(ConfigError) as e:
            config.load(require_secrets=False, guard=False)
        self.assertIn("section 5", str(e.exception))
        self.write("pilot.env", PILOT_ENV)
        (self.d / "publisher.env").unlink()
        with self.assertRaises(ConfigError) as e:
            config.load(guard=False)
        self.assertIn("pilot/pilot publisher-token", str(e.exception))

    def test_model_files_ignore_backups(self):
        cfg = config.load(guard=False)
        self.assertEqual([p.name for p in cfg.model_files], ["opencode.json", "p_api_key"])

    def test_mode_0644_rejected(self):
        self.write("opencode/p_api_key", "abc", 0o644)
        with self.assertRaises(ConfigError):
            config.load(guard=False)

    def test_dir_mode_0755_rejected(self):
        (self.d / "opencode").chmod(0o755)
        with self.assertRaises(ConfigError):
            config.load(guard=False)

    def test_literal_key_in_opencode_json_rejected(self):
        self.write("opencode/opencode.json", '{"providers": {"p": {"settings": {"apiKey": "sk-nope"}}}}')
        with self.assertRaises(ConfigError) as c:
            config.load(guard=False)
        self.assertNotIn("sk-nope", str(c.exception))

    def test_scm_like_key_file_rejected(self):
        self.write("opencode/github_api_key", "x")
        with self.assertRaises(ConfigError):
            config.load(guard=False)

    def test_missing_key_file_rejected(self):
        (self.d / "opencode/p_api_key").unlink()
        with self.assertRaises(ConfigError):
            config.load(guard=False)

    def test_retry_limit_3_rejected(self):
        self.write("pilot.env", PILOT_ENV + "RETRY_LIMIT=3\n")
        with self.assertRaises(ConfigError):
            config.load(guard=False)

    def test_guard_applied_on_load(self):
        self.write("pilot.env", PILOT_ENV.replace("foo-pilot-fixture", "specfoundry"))
        with self.assertRaises(ConfigError) as c:
            config.load()
        self.assertEqual(c.exception.code, 3)

    def test_secret_names_does_not_return_values(self):
        names = config.secret_names(self.d / "publisher.env")
        self.assertEqual(names, ["PILOT_SCM_TOKEN"])


if __name__ == "__main__":
    unittest.main()


class TestPublicRedactsHost(unittest.TestCase):
    def test_model_host_hashed_in_public_values(self):
        import hashlib
        cfg = config.Config(values={"PILOT_MODEL_EGRESS_HOSTS": "api.example.com,b.example.org", "PILOT_MODEL": "p/m"},
                            config_dir=Path("/x"), model_dir=Path("/x/opencode"), publisher_env=Path("/x/p.env"))
        pub = cfg.public()
        self.assertNotIn("example", pub["PILOT_MODEL_EGRESS_HOSTS"])
        self.assertEqual(pub["PILOT_MODEL_EGRESS_HOSTS"].split(",")[0],
                         "sha256:" + hashlib.sha256(b"api.example.com").hexdigest()[:16])
        self.assertEqual(pub["PILOT_MODEL"], "p/m")
