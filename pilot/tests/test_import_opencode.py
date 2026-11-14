"""`pilot import-opencode` (006 validation finding: reuse an existing OpenCode setup)."""
import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from specfoundry_pilot import config, import_opencode
from specfoundry_pilot.config import ConfigError

HOST = "llm.internal.example"


def host_config(**over):
    doc = {
        "$schema": "https://opencode.ai/config.json",
        "providers": {
            "corp": {"name": "Corp", "package": "@opencode/ai/providers/openai-compatible",
                     "settings": {"baseURL": f"https://{HOST}/v1",
                                  "apiKey": "{file:~/.config/opencode/corp_api_key}"},
                     "models": {"m1": {"name": "M1", "cost": {"input": 1, "output": 2}}}},
            "other": {"settings": {"baseURL": "https://other.example/v1", "apiKey": "literal-in-other"},
                      "models": {"x": {}}},
        },
        "mcp": {"some-server": {"type": "remote"}},
        "model": "corp/m1",
    }
    doc.update(over)
    return doc


class ImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.src, self.cfg = root / "host-opencode", root / "specfoundry"
        self.src.mkdir()
        self.write_src(host_config())
        (self.src / "corp_api_key").write_text("secret-value\n")
        (self.src / "unrelated_api_key").write_text("other\n")
        self.env = mock.patch.dict(os.environ, {"SPECFOUNDRY_CONFIG": str(self.cfg)})
        self.env.start()
        self.origin = mock.patch.object(config, "origin_repo", return_value="tosin2013/specfoundry")
        self.origin.start()

    def tearDown(self):
        self.origin.stop()
        self.env.stop()
        self.tmp.cleanup()

    def write_src(self, doc):
        (self.src / "opencode.json").write_text(json.dumps(doc))

    def run_import(self, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = import_opencode.run(self.src, **kw)
        return rc, buf.getvalue()

    def test_imports_only_the_model_provider(self):
        rc, out = self.run_import(fixture_repo="me/me-pilot-fixture")
        self.assertEqual(rc, 0)
        dest = self.cfg / "opencode"
        doc = json.loads((dest / "opencode.json").read_text())
        self.assertEqual(list(doc["providers"]), ["corp"])
        self.assertNotIn("mcp", doc)
        self.assertEqual(doc["providers"]["corp"]["models"]["m1"]["cost"], {"input": 1, "output": 2})
        self.assertEqual(sorted(p.name for p in dest.iterdir()), ["corp_api_key", "opencode.json"])
        self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
        for f in dest.iterdir():
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)
        self.assertIn("left out other providers: other", out)
        self.assertIn("mcp", out)

    def test_writes_pilot_env_without_printing_host(self):
        rc, out = self.run_import(fixture_repo="me/me-pilot-fixture")
        env = config.parse_env((self.cfg / "pilot.env").read_text())
        self.assertEqual(env["PILOT_MODEL"], "corp/m1")
        self.assertEqual(env["PILOT_MODEL_EGRESS_HOSTS"], HOST)
        self.assertEqual(env["PILOT_FIXTURE_REPO"], "me/me-pilot-fixture")
        self.assertEqual(stat.S_IMODE((self.cfg / "pilot.env").stat().st_mode), 0o600)
        self.assertNotIn(HOST, out)
        self.assertNotIn("secret-value", out)
        config.load(require_secrets=False)  # the result is a valid config

    def test_existing_pilot_env_is_compared_not_changed(self):
        self.cfg.mkdir()
        (self.cfg / "pilot.env").write_text("PILOT_FIXTURE_REPO=me/me-pilot-fixture\nPILOT_MODEL=corp/m1\n"
                                            "PILOT_MODEL_EGRESS_HOSTS=wrong.example\n")
        before = (self.cfg / "pilot.env").read_text()
        rc, out = self.run_import()
        self.assertEqual((self.cfg / "pilot.env").read_text(), before)
        self.assertIn("doesn't include your provider's host", out)
        self.assertNotIn(HOST, out)

    def test_refuses_literal_and_env_keys(self):
        for val, needle in (("sk-literal", "literal secret"), ("{env:CORP_KEY}", "{env:...}")):
            doc = host_config()
            doc["providers"]["corp"]["settings"]["apiKey"] = val
            self.write_src(doc)
            with self.assertRaises(ConfigError) as e:
                self.run_import()
            self.assertIn(needle, str(e.exception))
            self.assertNotIn("sk-literal", str(e.exception))
            self.assertFalse((self.cfg / "opencode").exists())

    def test_refuses_key_outside_worker_dir(self):
        doc = host_config()
        doc["providers"]["corp"]["settings"]["apiKey"] = "{file:~/keys/corp.txt}"
        self.write_src(doc)
        with self.assertRaises(ConfigError) as e:
            self.run_import()
        self.assertIn("_api_key", str(e.exception))

    def test_refuses_to_overwrite_without_force(self):
        self.run_import(fixture_repo="me/me-pilot-fixture")
        with self.assertRaises(ConfigError):
            self.run_import()
        rc, _ = self.run_import(force=True)
        self.assertEqual(rc, 0)

    def test_model_must_exist(self):
        with self.assertRaises(ConfigError) as e:
            self.run_import(model="corp/nope")
        self.assertIn("nope", str(e.exception))

    def test_fixture_repo_guard(self):
        with self.assertRaises(ConfigError) as e:
            self.run_import(fixture_repo="me/important-repo")
        self.assertEqual(e.exception.code, 3)


if __name__ == "__main__":
    unittest.main()
