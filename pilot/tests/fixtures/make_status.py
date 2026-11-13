"""Regenerate pilot/tests/fixtures/status/* from real `spec status --json` captures of
pilot/fixture (T014). Run: python3 pilot/tests/fixtures/make_status.py"""
import copy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "status"
FIXTURE = HERE.parents[1] / "fixture"


def capture(root):
    r = subprocess.run(["spec", "status", "--json", "--root", str(root)], capture_output=True, text=True)
    return json.loads(r.stdout)


def main():
    OUT.mkdir(exist_ok=True)
    base = capture(FIXTURE)
    with tempfile.TemporaryDirectory() as t:
        shutil.copytree(FIXTURE, t, dirs_exist_ok=True)
        rm = Path(t, ".specify/memory/roadmap.md")
        rm.write_text(rm.read_text().replace("### 001 — Slug function  [status: planned]",
                                             "### 001 — Slug function  [status: verified]"))
        after = capture(t)
    def item(d, i):
        return next(x for x in d["items"] if x["id"] == i)
    cases = {"ready_A": base, "blocked_B": base, "ready_B_after_verify": after}
    d = copy.deepcopy(base); d["schema_version"] = "1.1"; cases["schema_1_1"] = d
    d = copy.deepcopy(base); d["complete"] = False; cases["incomplete"] = d
    d = copy.deepcopy(base); d["error"] = {"code": "SS_X", "message": "boom"}; cases["error_set"] = d
    d = copy.deepcopy(base); d["items"] = [x for x in d["items"] if x["id"] != "001"]; cases["item_missing"] = d
    d = copy.deepcopy(base); d["items"].append(copy.deepcopy(item(d, "001"))); cases["item_duplicate"] = d
    d = copy.deepcopy(base); item(d, "001")["status_known"] = False; cases["status_unknown"] = d
    d = copy.deepcopy(base); item(d, "001")["active"] = False; cases["inactive"] = d
    d = copy.deepcopy(after); cases["already_verified"] = d
    d = copy.deepcopy(base); item(d, "001")["status"] = "implemented"; cases["already_implemented"] = d
    d = copy.deepcopy(base); d["diagnostics"].append({"code": "SS_TASK_FILE_MISSING", "severity": "error",
        "message": "x", "source": None, "item_id": "001", "related": []}); cases["item_error_diag"] = d
    d = copy.deepcopy(base); d["summary"]["blocked_count"] = 0; cases["inconsistent_count"] = d
    d = copy.deepcopy(base); item(d, "001")["status"] = "deferred"; cases["not_startable"] = d
    for name, data in cases.items():
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
    (OUT / "malformed.txt").write_text('{"schema_version": "1.0", "items": [\n')
    print(f"wrote {len(cases) + 1} files to {OUT}")


if __name__ == "__main__":
    main()
