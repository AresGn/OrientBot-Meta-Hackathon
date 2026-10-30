import pytest

from src.domain.guide import load_offer_rows
from src.domain.offer_subjects import (
    STATUS_CALCULABLE,
    STATUS_CONCOURS,
    STATUS_NOT_CALCULABLE,
    SUBJECTS_NOT_PUBLISHED,
    OfferSubjectsError,
    parse_subjects_by_series,
    subjects_for_serie,
)

ROWS = {row["Offre_ID"]: row for row in load_offer_rows()}
MEDICINE_SUBJECTS = ["Mathématiques", "Sciences Physiques (PCT/SPCT)", "SVT"]


def test_pub_062_gives_maths_pct_svt_for_series_c_and_d():
    parsed = parse_subjects_by_series(ROWS["PUB-062"]["Matières"])

    assert parsed["C"] == MEDICINE_SUBJECTS
    assert parsed["D"] == MEDICINE_SUBJECTS


def test_pub_077_glued_svt_deat_header_is_corrected():
    parsed = parse_subjects_by_series(ROWS["PUB-077"]["Matières"])

    assert parsed["C"] == ["Français", "Sciences Physiques (PCT/SPCT)", "SVT"]
    assert parsed["D"] == ["Français", "Sciences Physiques (PCT/SPCT)", "SVT"]
    assert parsed["DEAT/Pêche et aquaculture"] == ["Les trois (03) matières écrites"]
    assert all("SVTDEAT" not in subject for subjects in parsed.values() for subject in subjects)


@pytest.mark.parametrize("offre_id", ["PUB-220", "PUB-223"])
def test_unpublished_subjects_return_empty_parse(offre_id):
    assert parse_subjects_by_series(ROWS[offre_id]["Matières"]) == {}


@pytest.mark.parametrize("offre_id", ["PUB-219", "PUB-220", "PUB-221", "PUB-223", "PUB-224"])
def test_concours_offer_without_published_subjects_is_concours_not_unpublished(offre_id):
    row = ROWS[offre_id]
    assert row["Mode_entrée"] == "Concours"

    result = subjects_for_serie(row, "D")

    assert result["status"] == STATUS_CONCOURS
    assert result["subjects"] == []
    assert result["epreuves"] == []
    assert "notes du Bac ne suffisent pas" in result["reason"]


@pytest.mark.parametrize("serie", ["C", "D"])
def test_concours_offer_closed_to_the_serie_is_not_calculable(serie):
    row = ROWS["PUB-180"]  # Concours, segments G1 / A1, A2 / B only
    assert row["Mode_entrée"] == "Concours"

    result = subjects_for_serie(row, serie)

    assert result["status"] == STATUS_NOT_CALCULABLE
    assert serie in result["reason"]


def test_classement_offer_without_published_subjects_is_unpublished():
    result = subjects_for_serie(ROWS["PUB-145"], "D")  # Classement, Matières = "—"

    assert result["status"] == SUBJECTS_NOT_PUBLISHED
    assert result["subjects"] == []
    assert result["reason"] == SUBJECTS_NOT_PUBLISHED


def test_every_offer_is_analysed_without_guessing():
    assert len(ROWS) == 224
    unpublished = []
    for offre_id, row in ROWS.items():
        parsed = parse_subjects_by_series(row["Matières"])
        if not parsed:
            unpublished.append(offre_id)

    # data/offres_publiques_2026_2027.csv carries 8 "—" cells, not 2:
    # PUB-220 and PUB-223 plus the 6 "Toutes séries" rows (docs/decisions.md).
    assert sorted(unpublished) == [
        "PUB-145", "PUB-217", "PUB-218", "PUB-219",
        "PUB-220", "PUB-221", "PUB-223", "PUB-224",
    ]


@pytest.mark.parametrize("offre_id", ["PUB-085", "PUB-086"])
@pytest.mark.parametrize("serie", ["C", "D"])
def test_spanish_or_german_offers_are_not_calculable_with_reason(offre_id, serie):
    result = subjects_for_serie(ROWS[offre_id], serie)

    assert result["status"] == STATUS_NOT_CALCULABLE
    assert result["subjects"] == []
    assert "Espagnol ou Allemand" in result["reason"]


def test_concours_offer_lists_epreuves_without_assuming_bac_subjects():
    row = ROWS["PUB-021"]  # Concours: "C, D : Culture générale, Maths"
    assert row["Mode_entrée"] == "Concours"

    result = subjects_for_serie(row, "D")

    assert result["status"] == STATUS_CONCOURS
    assert result["subjects"] == []
    assert result["epreuves"] == ["Culture générale", "Maths"]
    assert "notes du Bac ne suffisent pas" in result["reason"]


def test_coverage_of_ok_classement_offers_is_reproducible():
    denominators = {"C": 0, "D": 0}
    calculable = {"C": 0, "D": 0}
    missing = {"C": set(), "D": set()}
    for row in ROWS.values():
        if row["Statut_qualité"] != "OK" or row["Mode_entrée"] != "Classement":
            continue
        for serie in ("C", "D"):
            if serie not in parse_subjects_by_series(row["Matières"]):
                continue
            denominators[serie] += 1
            result = subjects_for_serie(row, serie)
            if result["status"] == STATUS_CALCULABLE:
                calculable[serie] += 1
            else:
                missing[serie].add(row["Offre_ID"])

    # E3.5 (issue #24): PUB-085/086 and PUB-211..215 no longer carry an
    # invented Classement mode (the guide publishes a dash), so they leave
    # this Classement-only denominator; every remaining row is calculable.
    assert denominators == {"C": 142, "D": 143}
    assert calculable == {"C": 142, "D": 143}
    assert missing == {"C": set(), "D": set()}


def test_glued_and_semicolon_separated_headers_are_split():
    parsed = parse_subjects_by_series(
        "C, D : Anglais, Français, MathsG2, G3 : Anglais, Etude de Cas, Français"
    )
    assert parsed["C"] == ["Anglais", "Français", "Mathématiques"]
    assert parsed["G2"] == ["Anglais", "Etude de Cas", "Français"]


def test_unknown_subject_labels_are_kept_verbatim_not_invented():
    parsed = parse_subjects_by_series("C, D : Culture générale, Maths")

    assert parsed["D"] == ["Culture générale", "Mathématiques"]


def test_unparseable_header_raises_explicit_error():
    with pytest.raises(OfferSubjectsError):
        parse_subjects_by_series("Matieres sans en-tete: Maths, PCT, SVT")


def test_absent_serie_and_unsupported_serie_give_a_reason():
    absent = subjects_for_serie(ROWS["PUB-062"], "B")
    assert absent["status"] == STATUS_NOT_CALCULABLE
    assert "B" in absent["reason"]

    unsupported = subjects_for_serie(ROWS["PUB-062"], "A1")
    assert unsupported["status"] == STATUS_NOT_CALCULABLE
    assert unsupported["reason"]
