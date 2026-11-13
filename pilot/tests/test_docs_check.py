"""Docs check (006 T003, contracts/docs-check.md), including analysis H1 (no false positives)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("docs_check", ROOT / "pilot/tools/docs_check.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


class DocsCheckTest(unittest.TestCase):
    def check(self, text):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "doc.md"
            p.write_text(text)
            return dc.check_files([p])

    def assertClean(self, text):
        self.assertEqual(self.check(text), [])

    def assertFlags(self, text, needle):
        errs = self.check(text)
        self.assertTrue(errs, "expected a failure")
        self.assertTrue(any(needle in e for e in errs), errs)
        self.assertTrue(all(":" in e.split(" ")[0] for e in errs), errs)  # file:line prefix


class TestD1Commands(DocsCheckTest):
    def test_known(self):
        self.assertClean("```sh\npilot/pilot run\npilot/pilot up --local-build\npilot/pilot gate A --root x\n```\n")

    def test_unknown_flag(self):
        self.assertFlags("```sh\npilot/pilot run --bogus\n```\n", "--bogus")

    def test_unknown_subcommand(self):
        self.assertFlags("```bash\ncd ~/specfoundry && pilot/pilot frobnicate\n```\n", "frobnicate")

    def test_text_blocks_ignored(self):
        self.assertClean("```text\npilot/pilot frobnicate\n```\n")


class TestD2Paths(DocsCheckTest):
    def test_existing(self):
        self.assertClean("See `pilot/pins.env` and [the guide](docs/harnesses.md).\n")

    def test_missing(self):
        self.assertFlags("Edit `pilot/images/lock` first.\n", "pilot/images/lock")

    def test_missing_link(self):
        self.assertFlags("[x](specs/999-nope/spec.md)\n", "specs/999-nope")

    def test_not_paths_h1(self):
        # Domains, owner/repo slugs, home paths, placeholders and URLs are not repo paths.
        self.assertClean(
            "`ghcr.io/tosin2013/specfoundry-pilot-worker@sha256:abc` `tosin2013/craz3-pilot-fixture` "
            "`anomalyco/opencode` `kelos-dev/kelos` `~/.config/specfoundry/pilot.env` "
            "`<owner>/<name>-pilot-fixture` `https://github.com/x/y` `refs/heads/main` "
            "`localhost:5001/pilot-worker` `/etc/containerd/certs.d`\n")


class TestD3Versions(DocsCheckTest):
    def test_match(self):
        self.assertClean("Installs kind v0.27.0 and kubectl v1.32.2; Calico v3.29.3; spec 0.2.0; OpenCode v2.2.7.\n")

    def test_mismatch(self):
        self.assertFlags("Installs kind v0.26.0.\n", "kind")


class TestD4Secrets(DocsCheckTest):
    def test_token_like(self):
        self.assertFlags("token: " + "gh" + "p_" + "a" * 30 + "\n", "token-like")

    def test_plain_text(self):
        self.assertClean("Paste the token into the hidden prompt; never into chat.\n")


class TestMain(unittest.TestCase):
    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as t:
            good, bad = Path(t) / "g.md", Path(t) / "b.md"
            good.write_text("`pilot/pins.env`\n")
            bad.write_text("`pilot/nope.txt`\n")
            self.assertEqual(dc.main([str(good)]), 0)
            self.assertEqual(dc.main([str(bad)]), 1)


if __name__ == "__main__":
    unittest.main()
