"""Visible tests: basic behaviour only. The grader also runs hidden acceptance tests."""
import importlib.util

import pytest


def _has(mod):
    return importlib.util.find_spec(mod) is not None


@pytest.mark.skipif(not _has("slugkit.slug"), reason="slugify not implemented yet")
def test_slugify_lowercases_and_strips():
    from slugkit import slugify
    s = slugify("  Hello World  ")
    assert s == s.lower()
    assert "hello" in s and "world" in s
    assert not s.startswith((" ",)) and not s.endswith((" ",))


@pytest.mark.skipif(not _has("slugkit.unique"), reason="unique_slug not implemented yet")
def test_unique_slug_returns_base_when_free():
    from slugkit import slugify, unique_slug
    assert unique_slug("Hello World", set()) == slugify("Hello World")
