"""Prompt building and the declared induction (T024, research R6, FR-009c)."""
import hashlib
import unittest
from pathlib import Path

from specfoundry_pilot import prompt

FIX = Path(__file__).resolve().parents[1] / "fixture" / "specs" / "001-slugify"
SPEC = (FIX / "spec.md").read_text()
TASKS = (FIX / "tasks.md").read_text()
PLAN = (FIX / "plan.md").read_text()


class TestPrompt(unittest.TestCase):
    def test_full_prompt_contains_everything(self):
        text, ind = prompt.build_prompt(SPEC, TASKS, PLAN, None)
        self.assertIsNone(ind)
        self.assertIn(SPEC.strip(), text)
        self.assertIn(TASKS.strip(), text)
        self.assertIn("## Acceptance details", text)

    def test_induction_removes_only_the_section(self):
        text, ind = prompt.build_prompt(SPEC, TASKS, PLAN, prompt.INDUCTION)
        self.assertNotIn("## Acceptance details", text)
        self.assertNotIn("SLUG_MAX = 37", text)
        self.assertNotIn("n~a", text)
        self.assertIn("## Behaviour", text)
        self.assertIn("## Done when", text)
        self.assertIn(TASKS.strip(), text)
        self.assertEqual(ind["name"], "withheld-acceptance-section")
        self.assertEqual(ind["removed_heading"], "## Acceptance details")
        # removing the span from the spec yields exactly the spec text in the prompt
        start = SPEC.index("## Acceptance details")
        end = SPEC.index("\n## ", start + 1) + 1
        removed = SPEC[start:end]
        self.assertEqual(ind["removed_sha256"], hashlib.sha256(removed.encode()).hexdigest())
        self.assertEqual(ind["removed_bytes"], len(removed.encode()))
        self.assertIn((SPEC[:start] + SPEC[end:]).strip(), text)

    def test_section_sha_matches_full_prompt(self):
        full, _ = prompt.build_prompt(SPEC, TASKS, PLAN, None)
        _, ind = prompt.build_prompt(SPEC, TASKS, PLAN, prompt.INDUCTION)
        self.assertEqual(prompt.section_sha256(full), ind["removed_sha256"])

    def test_induction_requires_heading(self):
        with self.assertRaises(ValueError):
            prompt.build_prompt(SPEC.replace("## Acceptance details", "## Other"), TASKS, PLAN, prompt.INDUCTION)

    def test_unknown_induction(self):
        with self.assertRaises(ValueError):
            prompt.build_prompt(SPEC, TASKS, PLAN, "something-else")


if __name__ == "__main__":
    unittest.main()
