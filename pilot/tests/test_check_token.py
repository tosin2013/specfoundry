"""Publisher token scope check against a fake GitHub API."""
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("check_token", Path(__file__).resolve().parents[1] / "images/tools/check_token.py")
ct = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ct)

REPO, CANARY = "o/x-pilot-fixture", "o/specfoundry"


def fake(user=200, repo_push=True, pulls=200, canary=(200, False), expires="2026-11-20 00:00:00 UTC",
         repo_write=201, canary_write=404):
    def get(path, token, method="GET", body=None):
        if method == "POST" and path == f"/repos/{REPO}/git/blobs":
            return repo_write, None, {}
        if method == "POST" and path == f"/repos/{CANARY}/git/blobs":
            return canary_write, None, {}
        if path == "/user":
            return user, ({"login": "bot"} if user == 200 else None), {"github-authentication-token-expiration": expires}
        if path == f"/repos/{REPO}":
            return 200, {"permissions": {"push": repo_push}}, {}
        if path.startswith(f"/repos/{REPO}/pulls"):
            return pulls, [], {}
        if path == f"/repos/{CANARY}":
            return canary[0], ({"permissions": {"push": canary[1]}} if canary[0] == 200 else None), {}
        raise AssertionError(path)
    return get


class TestCheckToken(unittest.TestCase):
    def test_ok(self):
        r = ct.check("t", REPO, CANARY, get=fake())
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["login"], r["expires"], r["canary_push"]), ("bot", "2026-11-20 00:00:00 UTC", False))

    def test_public_canary_reports_owner_push_but_token_cannot_write(self):
        # 2026-11-13: for a PUBLIC canary, GET /repos reports the *account's* push permission;
        # only an actual write probe shows what the fine-grained token can do.
        r = ct.check("t", REPO, CANARY, get=fake(canary=(200, True), canary_write=404))
        self.assertTrue(r["ok"], r)
        self.assertFalse(r["canary_push"])

    def test_token_that_can_write_canary_fails(self):
        r = ct.check("t", REPO, CANARY, get=fake(canary_write=201))
        self.assertFalse(r["ok"])

    def test_token_that_cannot_write_fixture_fails(self):
        r = ct.check("t", REPO, CANARY, get=fake(repo_write=403))
        self.assertFalse(r["ok"])

    def test_canary_hidden_is_ok(self):
        self.assertTrue(ct.check("t", REPO, CANARY, get=fake(canary=(404, None)))["ok"])

    def test_problems(self):
        for kw in ({"user": 401}, {"repo_write": 403}, {"pulls": 403}, {"canary_write": 201}):
            with self.subTest(kw):
                r = ct.check("t", REPO, CANARY, get=fake(**kw))
                self.assertFalse(r["ok"])
                self.assertTrue(r["problems"])

    def test_output_never_contains_token(self):
        import json
        r = ct.check("SECRETVALUE123", REPO, CANARY, get=fake())
        self.assertNotIn("SECRETVALUE123", json.dumps(r))


if __name__ == "__main__":
    unittest.main()
