"""Regression: prompts must read a real terminal (2026-11-13 live run declined every prompt)."""
import os
import shutil
import subprocess
import unittest
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1]
CODE = "from specfoundry_pilot.reconcile import ask_tty; print('ANSWER=' + repr(ask_tty('Q? ').strip()))"


@unittest.skipUnless(shutil.which("script"), "needs util-linux script(1) for a pseudo-terminal")
class TestAskTty(unittest.TestCase):
    def run_in_pty(self, typed: str) -> str:
        env = {**os.environ, "PYTHONPATH": str(PILOT)}
        r = subprocess.run(["script", "-qc", f'python3 -c "{CODE}"', "/dev/null"], input=typed,
                           capture_output=True, text=True, env=env, timeout=30)
        return r.stdout

    def test_reads_y_from_terminal(self):
        self.assertIn("ANSWER='y'", self.run_in_pty("y\n"))

    def test_reads_n_from_terminal(self):
        self.assertIn("ANSWER='N'", self.run_in_pty("N\n"))

    def test_no_terminal_declines(self):
        env = {**os.environ, "PYTHONPATH": str(PILOT)}
        r = subprocess.run(["setsid", "python3", "-c", CODE], capture_output=True, text=True, env=env,
                           stdin=subprocess.DEVNULL, timeout=30)
        self.assertIn("ANSWER=''", r.stdout)


if __name__ == "__main__":
    unittest.main()
