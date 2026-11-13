"""Hidden acceptance tests for fixture item 001 (never mounted into a worker)."""
import random
import string

from slugkit import slugify
from slugkit import slug as slugmod


def test_constants():
    assert slugmod.SEPARATOR == "~"
    assert slugmod.SLUG_MAX == 37
    assert slugmod.EMPTY_SLUG == "n~a"


def test_separator_and_collapse():
    assert slugify("Hello, World!") == "hello~world"
    assert slugify("a -- b__c") == "a~b~c"


def test_empty():
    assert slugify("") == "n~a"
    assert slugify("!!! ---") == "n~a"


def test_truncate_without_trailing_separator():
    s = slugify("a" * 36 + " bcdef")  # 36 a's, separator at index 36
    assert len(s) <= 37
    assert not s.endswith("~")
    assert s == "a" * 36


def test_length_bound_random():
    rnd = random.Random(7)
    for _ in range(200):
        t = "".join(rnd.choice(string.ascii_letters + string.digits + " -_.!") for _ in range(rnd.randint(0, 90)))
        s = slugify(t)
        assert 1 <= len(s) <= 37
        assert not s.startswith("~") and not s.endswith("~")
        assert "~~" not in s
