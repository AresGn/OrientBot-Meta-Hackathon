import re
import unicodedata

# Canonical names are the ones used in data/coefficients_bac_benin.json (series C and D).
# Aliases only rename a subject; no coefficient lives here.
SUBJECT_ALIASES: dict[str, tuple[str, ...]] = {
    "Mathématiques": ("mathematiques", "mathematique", "maths", "math"),
    "Sciences Physiques (PCT/SPCT)": (
        "sciences physiques", "science physique", "pct", "spct", "pct spct", "physique chimie",
        "physique chimie technologie", "physique chimie et technologie", "sciences physiques pct", "sciences physiques spct",
    ),
    "Français": ("francais", "fr"),
    "Anglais": ("anglais", "anglais lv1", "lv1 anglais", "langue vivante 1 anglais"),
    "SVT": ("svt", "sciences de la vie et de la terre"),
    "Histoire-Géographie": ("histoire geographie", "hist geo", "histgeo", "hg", "histoire geo"),
    "Philosophie": ("philosophie", "philo"),
}


class UnknownSubjectError(ValueError):
    """Raised when a subject name matches no known alias; we never guess."""


def _to_key(raw: str) -> str:
    decomposed = unicodedata.normalize("NFD", raw.casefold())
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_accents).split())


_CANONICAL_BY_KEY: dict[str, str] = {
    _to_key(alias): canonical
    for canonical, aliases in SUBJECT_ALIASES.items()
    for alias in (canonical, *aliases)
}


def normalize_subject(raw: str) -> str:
    """Return the canonical subject name for a transcript, guide or JSON spelling."""
    key = _to_key(raw) if isinstance(raw, str) else ""
    if key in _CANONICAL_BY_KEY:
        return _CANONICAL_BY_KEY[key]
    # Plural written by hand ("philosophies"); never applied to a key that already matched.
    if key.endswith("s") and key[:-1] in _CANONICAL_BY_KEY:
        return _CANONICAL_BY_KEY[key[:-1]]
    raise UnknownSubjectError(f"unknown subject: {raw!r}")
