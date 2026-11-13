from .slug import SEPARATOR, SLUG_MAX, slugify


def unique_slug(text: str, existing: set) -> str:
    base = slugify(text)
    if base not in existing:
        return base
    n = 2
    while True:
        suffix = f"{SEPARATOR}{n}"
        cand = base[: SLUG_MAX - len(suffix)].rstrip(SEPARATOR) + suffix
        if cand not in existing:
            return cand
        n += 1
