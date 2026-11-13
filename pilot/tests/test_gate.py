"""Gate fail-closed matrix (US1, SC-005, research R3)."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from specfoundry_pilot import gate

FX = Path(__file__).resolve().parent / "fixtures" / "status"
SCHEMA = json.loads((Path(__file__).resolve().parents[2] /
                     "specs/002-m1-gated-pilot/contracts/gate-decision.schema.json").read_text())


def fx(name):
    return (FX / name).read_text()


CASES = [
    # (fixture, task, item, expected decision, expected reasons)
    ("ready_A.json", "A", "001", "allow", ["OK"]),
    ("blocked_B.json", "B", "002", "refuse", ["DEP_UNSATISFIED:001"]),
    ("ready_B_after_verify.json", "B", "002", "allow", ["OK"]),
    ("schema_1_1.json", "A", "001", "refuse", ["SCHEMA_MISMATCH"]),
    ("incomplete.json", "A", "001", "refuse", ["INCOMPLETE"]),
    ("error_set.json", "A", "001", "refuse", ["UNEVALUABLE:tool_error"]),
    ("item_missing.json", "A", "001", "refuse", ["ITEM_MISSING"]),
    ("item_duplicate.json", "A", "001", "refuse", ["ITEM_DUPLICATE"]),
    ("status_unknown.json", "A", "001", "refuse", ["STATUS_UNKNOWN"]),
    ("inactive.json", "A", "001", "refuse", ["INACTIVE"]),
    ("already_verified.json", "A", "001", "refuse", ["ALREADY_VERIFIED"]),
    ("already_implemented.json", "A", "001", "refuse", ["ALREADY_IMPLEMENTED"]),
    ("item_error_diag.json", "A", "001", "refuse", ["ITEM_ERROR_DIAGNOSTIC:SS_TASK_FILE_MISSING"]),
    ("inconsistent_count.json", "B", "002", "refuse", ["DEP_UNSATISFIED:001", "INCONSISTENT_BLOCKED_COUNT"]),
    ("not_startable.json", "A", "001", "refuse", ["STATUS_NOT_STARTABLE:deferred"]),
    ("malformed.txt", "A", "001", "refuse", ["UNEVALUABLE:bad_json"]),
]


def validate(decision):
    """Minimal stdlib check against contracts/gate-decision.schema.json."""
    for k in SCHEMA["required"]:
        assert k in decision, f"missing {k}"
    assert set(decision) <= set(SCHEMA["properties"]), f"extra keys {set(decision) - set(SCHEMA['properties'])}"
    assert decision["version"] == 1
    assert decision["task"] in ("A", "B")
    assert decision["decision"] in ("allow", "refuse")
    pat = re.compile(SCHEMA["properties"]["reasons"]["items"]["pattern"])
    assert decision["reasons"], "reasons empty"
    for r in decision["reasons"]:
        assert pat.match(r), f"bad reason {r}"
    for k in SCHEMA["properties"]["input"]["required"]:
        assert k in decision["input"], f"input missing {k}"
    assert (decision["decision"] == "allow") == (decision["reasons"] == ["OK"])


class TestDecide(unittest.TestCase):
    def test_matrix(self):
        for name, task, item, want, reasons in CASES:
            with self.subTest(name):
                d, r = gate.decide(item, 0, fx(name))
                self.assertEqual((d, r), (want, reasons))

    def test_exit_code_2_refuses_even_with_ready_json(self):
        self.assertEqual(gate.decide("001", 2, fx("ready_A.json")), ("refuse", ["UNEVALUABLE:exit_2"]))

    def test_exit_code_1_is_evaluable(self):
        self.assertEqual(gate.decide("001", 1, fx("ready_A.json")), ("allow", ["OK"]))

    def test_other_exit_codes_refuse(self):
        self.assertEqual(gate.decide("001", 127, ""), ("refuse", ["UNEVALUABLE:exit_127"]))
        self.assertEqual(gate.decide("001", None, ""), ("refuse", ["UNEVALUABLE:spawn_failed"]))

    def test_empty_stdout(self):
        self.assertEqual(gate.decide("001", 0, ""), ("refuse", ["UNEVALUABLE:empty"]))

    def test_non_object_json(self):
        self.assertEqual(gate.decide("001", 0, "[]"), ("refuse", ["SCHEMA_MISMATCH"]))

    def test_garbage_item_shapes_refuse_not_crash(self):
        d = json.loads(fx("ready_A.json"))
        d["items"][0]["dependencies"] = [{"id": "x"}]  # missing satisfied
        dec, reasons = gate.decide("001", 0, json.dumps(d))
        self.assertEqual(dec, "refuse")


class TestEvaluate(unittest.TestCase):
    def _root(self, tmp):
        import shutil
        shutil.copytree(Path(__file__).resolve().parents[1] / "fixture", tmp, dirs_exist_ok=True)
        return tmp

    def test_real_spec_status_on_fixture(self):
        with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as out:
            root = self._root(t)
            a = gate.evaluate("A", "001", root, seq=1, out_dir=Path(out), repo="local")
            b = gate.evaluate("B", "002", root, seq=2, out_dir=Path(out), repo="local")
            self.assertEqual(a["decision"], "allow")
            self.assertEqual((b["decision"], b["reasons"]), ("refuse", ["DEP_UNSATISFIED:001"]))
            for d in (a, b):
                validate(d)
            self.assertTrue((Path(out) / "1-A.json").exists())
            self.assertTrue((Path(out) / "2-B.status.json").exists())

    def test_spawn_failure_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            d = gate.evaluate("A", "001", self._root(t), seq=1, spec_bin="/nonexistent/spec", repo="local")
            self.assertEqual((d["decision"], d["reasons"]), ("refuse", ["UNEVALUABLE:spawn_failed"]))
            validate(d)

    def test_tool_failure_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            d = gate.evaluate("A", "001", self._root(t), seq=1, spec_bin="/bin/false", repo="local")
            self.assertEqual(d["decision"], "refuse")
            validate(d)

    def test_missing_roadmap_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            d = gate.evaluate("A", "001", t, seq=1, repo="local")
            self.assertEqual(d["decision"], "refuse")
            validate(d)

    def test_truncated_roadmap_refuses_b(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._root(t)
            rm = Path(root, ".specify/memory/roadmap.md")
            text = rm.read_text()
            rm.write_text(text[: text.index("### 002")] + "### 002 — Unique sl")
            d = gate.evaluate("B", "002", root, seq=1, repo="local")
            self.assertEqual(d["decision"], "refuse")
            validate(d)


if __name__ == "__main__":
    unittest.main()
