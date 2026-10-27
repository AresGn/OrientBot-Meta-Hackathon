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


SHEET_LABELS = [
    "ANGLAIS", "FRANCAIS", "HISTOIRE & GEOGRAPHIE", "MATHEMATIQUES", "PHILOSOPHIE",
    "PHYSIQUE, CHIMIE ET TECHNOLOGIE", "SCIENCES DE LA VIE ET DE LA TERRE",
]  # labels printed on data/samples/releve_serie_c.jpg and releve_serie_d.jpg


@pytest.mark.parametrize("serie", ["C", "D"])
def test_printed_sheet_labels_resolve_to_ranking_subjects(serie):
    from src.domain.coefficients import load_coefficients

    assert {normalize_subject(label) for label in SHEET_LABELS} == set(load_coefficients(serie))


@pytest.mark.parametrize("raw", ["Langue vivante 1", "Sciences naturelles"])
def test_ambiguous_names_are_not_guessed(raw):
    with pytest.raises(UnknownSubjectError):
        normalize_subject(raw)
