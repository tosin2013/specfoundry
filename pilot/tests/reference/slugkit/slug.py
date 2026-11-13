import re

SEPARATOR = "~"
SLUG_MAX = 37
EMPTY_SLUG = "n~a"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", SEPARATOR, text.lower()).strip(SEPARATOR)
    s = s[:SLUG_MAX].rstrip(SEPARATOR)
    return s or EMPTY_SLUG
