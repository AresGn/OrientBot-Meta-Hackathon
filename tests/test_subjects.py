import pytest

from src.domain.subjects import SUBJECT_ALIASES, UnknownSubjectError, normalize_subject

ALIAS_CASES = [
    ("Maths", "Mathématiques"),
    ("MATH", "Mathématiques"),
    ("mathematiques", "Mathématiques"),
    ("Mathématiques", "Mathématiques"),
    ("PCT", "Sciences Physiques (PCT/SPCT)"),
    ("SPCT", "Sciences Physiques (PCT/SPCT)"),
    ("Sciences Physiques (PCT/SPCT)", "Sciences Physiques (PCT/SPCT)"),
    ("Sciences physiques", "Sciences Physiques (PCT/SPCT)"),
    ("Physique-Chimie", "Sciences Physiques (PCT/SPCT)"),
    ("Anglais (LV1)", "Anglais"),
    ("anglais", "Anglais"),
    ("Français", "Français"),
    ("FRANCAIS", "Français"),
    ("SVT", "SVT"),
    ("Sciences de la Vie et de la Terre", "SVT"),
    ("Hist-Géo", "Histoire-Géographie"),
    ("Histoire-Géographie", "Histoire-Géographie"),
    ("histoire geographie", "Histoire-Géographie"),
    ("Philo", "Philosophie"),
    ("Philosophies", "Philosophie"),
]


@pytest.mark.parametrize("raw, expected", ALIAS_CASES)
def test_alias_resolves_to_canonical_subject(raw, expected):
    assert normalize_subject(raw) == expected


def test_every_canonical_subject_is_covered_by_an_alias_case():
    assert set(SUBJECT_ALIASES) == {expected for _, expected in ALIAS_CASES}


@pytest.mark.parametrize("raw", ["Couture", "Mathématiques avancées", "", "EPS", "Français (oral)"])
def test_unknown_subject_raises_explicit_error(raw):
    with pytest.raises(UnknownSubjectError):
        normalize_subject(raw)


def test_non_string_subject_raises_explicit_error():
    with pytest.raises(UnknownSubjectError):
        normalize_subject(None)
