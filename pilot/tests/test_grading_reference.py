"""The hidden grading tests must be passable: run them against a reference solution.

Also proves the induction is meaningful: a solution that follows only the spec text
outside "Acceptance details" (dash separator, no length cap) fails them.
"""
import importlib
import sys
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRADING = HERE.parent / "grading"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, GRADING / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_all(mod):
    failures = []
    for k in dir(mod):
        if k.startswith("test_"):
            try:
                getattr(mod, k)()
            except Exception as e:  # noqa: BLE001 - any failure counts
                failures.append((k, e))
    return failures


class _SysPath:
    def __init__(self, path, purge=("slugkit",)):
        self.path, self.purge = str(path), purge

    def __enter__(self):
        for m in list(sys.modules):
            if m.split(".")[0] in self.purge:
                del sys.modules[m]
        sys.path.insert(0, self.path)

    def __exit__(self, *a):
        sys.path.remove(self.path)
        for m in list(sys.modules):
            if m.split(".")[0] in self.purge:
                del sys.modules[m]


class TestHiddenGradingIsPassable(unittest.TestCase):
    def test_reference_passes_001_and_002(self):
        with _SysPath(HERE / "reference"):
            for name in ("test_hidden_001", "test_hidden_002"):
                self.assertEqual(_run_all(_load(name)), [], name)

    def test_naive_solution_fails_001(self):
        import re
        naive = types.ModuleType("slugkit")
        slug = types.ModuleType("slugkit.slug")
        slug.slugify = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
        naive.slugify = slug.slugify
        naive.slug = slug
        for m in list(sys.modules):
            if m.split(".")[0] == "slugkit":
                del sys.modules[m]
        sys.modules["slugkit"], sys.modules["slugkit.slug"] = naive, slug
        try:
            self.assertTrue(_run_all(_load("test_hidden_001")))
        finally:
            del sys.modules["slugkit"], sys.modules["slugkit.slug"]


if __name__ == "__main__":
    unittest.main()
