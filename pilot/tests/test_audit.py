"""Evidence-only audit AU01-AU11 (T050, contracts/evidence-record.md)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from specfoundry_pilot import audit
from tests import evidence_builder


def load_events(d):
    return [json.loads(l) for l in (d / "events.jsonl").read_text().splitlines()]


def save_events(d, ev):
    for i, e in enumerate(ev, 1):
        e["seq"] = i
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ev))


def mutate_events(fn):
    def m(d):
        ev = load_events(d)
        save_events(d, fn(ev))
    return m


def drop(pred):
    return mutate_events(lambda ev: [e for e in ev if not pred(e)])


def b_attempt_first(ev):
    i = next(i for i, e in enumerate(ev) if e["event"] == "task_verified")
    x = {"stage": "attempt", "task": "B", "attempt": 1, "event": "attempt_created", "detail": "", "at": ""}
    return ev[:i] + [x] + ev[i:]


def mode_after_a1(ev):
    m = next(e for e in ev if e["event"] == "mode_confirmed")
    ev = [e for e in ev if e is not m]
    i = next(i for i, e in enumerate(ev) if e["stage"] == "attempt") + 1
    return ev[:i] + [m] + ev[i:]


def edit_json(rel, fn):
    def m(d):
        p = d / rel
        p.write_text(json.dumps(fn(json.loads(p.read_text()))))
    return m


def edit_jsonl(rel, fn):
    def m(d):
        p = d / rel
        rows = [json.loads(l) for l in p.read_text().splitlines()]
        p.write_text("".join(json.dumps(r) + "\n" for r in fn(rows)))
    return m


def fail_row(prefix):
    return edit_jsonl("checks/results.jsonl", lambda rows: [dict(r, result="fail") if r["id"] == prefix and r["detail"] == "A-2" or (r["id"] == prefix and prefix.startswith("GM")) else r for r in rows])


MUTATIONS = {
    "AU01": mutate_events(b_attempt_first),
    "AU02": drop(lambda e: e["event"] == "grade_fail"),
    "AU03": edit_json("prs.json", lambda p: p + [dict(p[0], task="A", number=3)]),
    "AU04": fail_row("P04"),
    "AU05": fail_row("GM02"),
    "AU06": edit_json("attempts/A-2/report.json", lambda r: {**r, "spend": {**r["spend"], "cap_mode": "cost", "cost_usd": 1.2}}),
    "AU07": edit_jsonl("teardown.jsonl", lambda rows: [dict(rows[0], result="fail")] + rows[1:]),
    "AU08": lambda d: (d / "attempts/A-2/notes.txt").write_text("token " + "github" + "_pat_" + "x" * 30),
    "AU09": drop(lambda e: e["event"] == "retry_confirmed"),
    "AU10": mutate_events(mode_after_a1),
    "AU11": lambda d: shutil.copy(d / "attempts/A-1/prompt.md", d / "attempts/A-2/prompt.md"),
}


class TestAudit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = evidence_builder.build(Path(self.tmp.name) / "20261113T000000Z")

    def tearDown(self):
        self.tmp.cleanup()

    def results(self, d):
        rows = audit.audit_dir(d, secret_files=[], final=True)
        return {r["id"]: r["result"] for r in rows}

    def test_good_run_all_pass(self):
        res = self.results(self.d)
        self.assertEqual(sorted(res), [f"AU{i:02d}" for i in range(1, 12)])
        self.assertEqual({k for k, v in res.items() if v != "pass"}, set(), res)

    def test_each_mutation_fails_exactly_its_check(self):
        for au, mutate in MUTATIONS.items():
            with self.subTest(au):
                d = Path(self.tmp.name) / f"m-{au}"
                shutil.copytree(self.d, d)
                mutate(d)
                failed = {k for k, v in self.results(d).items() if v != "pass"}
                self.assertEqual(failed, {au})

    def test_extra_pr_variants(self):
        for fn in (lambda p: [dict(p[0], draft=False), p[1]], lambda p: [dict(p[0], author="someone"), p[1]], lambda p: p[:1]):
            d = Path(self.tmp.name) / f"pr-{id(fn)}"
            shutil.copytree(self.d, d)
            edit_json("prs.json", fn)(d)
            self.assertEqual(self.results(d)["AU03"], "fail")

    def test_teardown_pending_when_not_final(self):
        (self.d / "teardown.jsonl").unlink()
        ids = {r["id"] for r in audit.audit_dir(self.d, secret_files=[], final=False)}
        self.assertNotIn("AU07", ids)
        self.assertEqual(self.results(self.d)["AU07"], "fail")


if __name__ == "__main__":
    unittest.main()
