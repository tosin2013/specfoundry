"""Hidden acceptance tests for fixture item 002 (never mounted into a worker)."""
from slugkit import slugify, unique_slug


def test_free_base():
    assert unique_slug("Hello World", set()) == "hello~world"


def test_suffix_sequence():
    taken = {"hello~world"}
    assert unique_slug("Hello World", taken) == "hello~world~2"
    taken.add("hello~world~2")
    assert unique_slug("Hello World", taken) == "hello~world~3"


def test_existing_not_modified():
    taken = {"abc"}
    unique_slug("abc", taken)
    assert taken == {"abc"}


def test_length_with_suffix():
    base = slugify("x" * 50)
    assert base == "x" * 37
    s = unique_slug("x" * 50, {base})
    assert s == "x" * 35 + "~2"
    assert len(s) <= 37


def test_cut_base_trailing_separator_removed():
    text = "a" * 34 + " b"  # slug: 34 a's + "~b" (36 chars)
    base = slugify(text)
    s = unique_slug(text, {base})
    assert len(s) <= 37 and "~~" not in s
    assert s == "a" * 34 + "~2"


def test_empty_taken():
    assert unique_slug("", {"n~a"}) == "n~a~2"
