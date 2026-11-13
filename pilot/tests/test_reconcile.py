"""Reconcile: propose -> approve -> apply (T025, research R9, FR-018)."""
import unittest
from pathlib import Path

from specfoundry_pilot import reconcile

ROADMAP = (Path(__file__).resolve().parents[1] / "fixture/.specify/memory/roadmap.md").read_text()


def make(merged=True, percent=100, files_equal=True, answer="y"):
    calls = {"pushed": 0}
    head_files = {"src/slugkit/slug.py": b"v1", "specs/001-slugify/tasks.md": b"done"}

    def pr_view(n):
        return {"state": "MERGED" if merged else "OPEN", "mergedAt": "2026-11-13T00:00:00Z" if merged else None,
                "mergeCommit": {"oid": "abc"} if merged else None}

    def default_file(path):
        return head_files[path] if files_equal else b"edited after grading"

    def push(text):
        calls["pushed"] += 1
        calls["text"] = text
        return "def456"

    r = reconcile.Reconciler(
        pr_view=pr_view, tasks_percent=lambda item: percent, default_file=default_file,
        graded_file=lambda p: head_files[p], roadmap_text=lambda: ROADMAP, push=push, ask=lambda q: answer)
    return r, calls


class TestReconcile(unittest.TestCase):
    PATHS = ["src/slugkit/slug.py", "specs/001-slugify/tasks.md"]

    def test_happy_path_applies_one_line(self):
        r, calls = make()
        code, rec = r.run("A", "001", 7, self.PATHS)
        self.assertEqual(code, 0)
        self.assertTrue(rec["approved"])
        self.assertEqual(rec["applied_commit"], "def456")
        self.assertEqual(calls["pushed"], 1)
        old, new = ROADMAP.splitlines(), calls["text"].splitlines()
        diff = [(a, b) for a, b in zip(old, new) if a != b]
        self.assertEqual(len(old), len(new))
        self.assertEqual(diff, [("### 001 — Slug function  [status: planned]",
                                 "### 001 — Slug function  [status: verified]")])

    def test_not_merged_exit_4(self):
        r, calls = make(merged=False)
        code, rec = r.run("A", "001", 7, self.PATHS)
        self.assertEqual((code, rec["reason"], calls["pushed"]), (4, "NOT_MERGED", 0))

    def test_tasks_incomplete_no_proposal(self):
        r, calls = make(percent=66)
        code, rec = r.run("A", "001", 7, self.PATHS)
        self.assertEqual((code, rec["reason"], rec["proposed"], calls["pushed"]), (1, "TASKS_INCOMPLETE", None, 0))

    def test_tree_mismatch_no_proposal(self):
        r, calls = make(files_equal=False)
        code, rec = r.run("A", "001", 7, self.PATHS)
        self.assertEqual((code, rec["reason"], rec["proposed"], calls["pushed"]), (1, "TREE_MISMATCH", None, 0))

    def test_operator_declines_exit_5(self):
        for ans in ("N", "", "no"):
            r, calls = make(answer=ans)
            code, rec = r.run("A", "001", 7, self.PATHS)
            self.assertEqual((code, rec["approved"], calls["pushed"]), (5, False, 0))

    def test_status_edit_requires_exactly_one_planned_heading(self):
        with self.assertRaises(ValueError):
            reconcile.status_edit(ROADMAP.replace("[status: planned]", "[status: specced]"), "001")
        with self.assertRaises(ValueError):
            reconcile.status_edit(ROADMAP, "009")


if __name__ == "__main__":
    unittest.main()
