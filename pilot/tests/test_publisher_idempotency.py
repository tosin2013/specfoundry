"""Publisher idempotency (T026, research R8, FR-014) against a stubbed GitHub."""
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "pilot_publish", Path(__file__).resolve().parents[1] / "images/tools/publish.py")
publish_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(publish_mod)

SPEC = {"repo": "o/x-pilot-fixture", "head": "pilot/20261113T000000Z/a", "base": "main",
        "base_revision": "abc", "title": "t", "body": "b", "run_id": "r", "task": "A"}


class FakeGitHub:
    def __init__(self, existing=None, fail_after_create=False):
        self.prs = list(existing or [])
        self.created = 0
        self.fail_after_create = fail_after_create

    def user_login(self):
        return "pilot-bot"

    def open_prs(self, repo, owner, head):
        return [p for p in self.prs if p["head"]["ref"] == head]

    def create_draft_pr(self, repo, head, base, title, body):
        self.created += 1
        pr = {"number": 10 + self.created, "html_url": f"https://github.com/{repo}/pull/{10 + self.created}",
              "head": {"ref": head}, "draft": True, "user": {"login": "pilot-bot"}}
        self.prs.append(pr)
        if self.fail_after_create:
            self.fail_after_create = False
            raise TimeoutError("lost response")
        return pr


class TestIdempotency(unittest.TestCase):
    def test_existing_pr_recorded_not_duplicated(self):
        gh = FakeGitHub(existing=[{"number": 7, "html_url": "u", "head": {"ref": SPEC["head"]}, "draft": True,
                                   "user": {"login": "pilot-bot"}}])
        pushes = []
        r = publish_mod.publish(gh, pushes.append, SPEC)
        self.assertEqual((r["created"], r["number"], gh.created, pushes), (False, 7, 0, []))

    def test_creates_exactly_one_draft(self):
        gh = FakeGitHub()
        pushes = []
        r = publish_mod.publish(gh, pushes.append, SPEC)
        self.assertEqual((r["created"], r["draft"], gh.created, len(pushes)), (True, True, 1, 1))
        self.assertEqual(r["token_login"], "pilot-bot")

    def test_rerun_after_failure_after_create(self):
        gh = FakeGitHub(fail_after_create=True)
        with self.assertRaises(TimeoutError):
            publish_mod.publish(gh, lambda s: None, SPEC)
        r = publish_mod.publish(gh, lambda s: None, SPEC)
        self.assertEqual((r["created"], gh.created, len(gh.prs)), (False, 1, 1))

    def test_no_merge_code_path(self):
        src = (Path(__file__).resolve().parents[1] / "images/tools/publish.py").read_text()
        self.assertNotIn("/merge", src)
        self.assertNotIn("merge_method", src)


if __name__ == "__main__":
    unittest.main()
