"""Spend-cap watchdog (R2, SC-008) using the real OpenCode 2.2.7 step_finish event shape."""
import importlib.util
import json
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("watchdog", Path(__file__).resolve().parents[1] / "images/worker/watchdog.py")
wd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wd)


def step(pid, cost, inp, out):
    return json.dumps({"type": "step_finish", "part": {"id": pid, "type": "step-finish", "reason": "stop", "cost": cost,
                                                       "tokens": {"input": inp, "output": out, "reasoning": 0,
                                                                  "cache": {"read": 0, "write": 0}}}})


class TestMeter(unittest.TestCase):
    def test_token_fallback_when_cost_zero(self):
        m = wd.Meter(1.0, 20000)
        self.assertFalse(m.feed(step("a", 0, 8850, 76)))
        self.assertFalse(m.feed('{"type":"text","part":{"text":"hi"}}'))
        self.assertFalse(m.feed("not json"))
        self.assertTrue(m.feed(step("b", 0, 11000, 100)))
        r = m.report()
        self.assertEqual((r["cap_mode"], r["tokens"], r["cost_usd"]), ("token-fallback", 20026, 0))

    def test_cost_mode(self):
        m = wd.Meter(1.0, 10)
        self.assertFalse(m.feed(step("a", 0.6, 100000, 10)))  # tokens over token_cap, but cost mode applies
        self.assertTrue(m.feed(step("b", 0.5, 100, 10)))
        self.assertEqual(m.report()["cap_mode"], "cost")

    def test_same_step_not_double_counted(self):
        m = wd.Meter(1.0, 10**9)
        m.feed(step("a", 0.4, 10, 1))
        m.feed(step("a", 0.4, 10, 1))
        self.assertAlmostEqual(m.cost, 0.4)


if __name__ == "__main__":
    unittest.main()
