import pytest

from src.tools.compute_ranking_average import compute_ranking_average

MEDECINE_SUBJECTS = ["SVT", "Maths", "PCT"]


def grades(svt, maths, pct):
    return [{"matiere": "SVT", "note": svt}, {"matiere": "Mathématiques", "note": maths},
            {"matiere": "PCT", "note": pct}]


def coefficients_of(result):
    return {d["matiere"]: d["coefficient"] for d in result["details"]}


def test_medecine_serie_d_uses_page_8_coefficients():
    result = compute_ranking_average("D", MEDECINE_SUBJECTS, grades(15, 12, 12))
    assert coefficients_of(result) == {"SVT": 5, "Mathématiques": 4, "Sciences Physiques (PCT/SPCT)": 4}
    assert result["somme_coefficients"] == 13
    assert result["moyenne"] == pytest.approx(171 / 13)
    assert result["moyenne_arrondie"] == 13.15


def test_medecine_serie_c_uses_page_8_coefficients():
    result = compute_ranking_average("C", MEDECINE_SUBJECTS, grades(15, 12, 12))
    assert coefficients_of(result) == {"SVT": 2, "Mathématiques": 6, "Sciences Physiques (PCT/SPCT)": 5}
    assert result["somme_coefficients"] == 13
    assert result["moyenne"] == pytest.approx((15 * 2 + 12 * 6 + 12 * 5) / 13)


def test_details_carry_the_provenance_of_each_coefficient():
    detail = compute_ranking_average("D", MEDECINE_SUBJECTS, grades(15, 12, 12))["details"][0]
    assert detail["provenance"] == {"fichier": "coefficients_bac_benin.json", "serie": "D", "matiere": "SVT"}


def test_missing_coefficient_is_not_computed_with_reason():
    result = compute_ranking_average("D", ["SVT", "Maths", "Économie"], grades(15, 12, 12))
    assert result["status"] == "non calculé"
    assert "Économie" in result["reason"]


def test_subject_without_coefficient_in_the_serie_is_not_computed():
    result = compute_ranking_average("D", ["SVT", "EPS"], grades(15, 12, 12))
    assert result["status"] == "non calculé"


def test_missing_grade_is_not_computed():
    result = compute_ranking_average("D", MEDECINE_SUBJECTS, grades(15, 12, 12)[:2])
    assert result == {"status": "non calculé", "reason": "note manquante: Sciences Physiques (PCT/SPCT)"}


@pytest.mark.parametrize("bad_note", [None, -1, 20.5, "12"])
def test_unreadable_or_out_of_range_grade_is_not_computed(bad_note):
    result = compute_ranking_average("D", MEDECINE_SUBJECTS, grades(bad_note, 12, 12))
    assert result["status"] == "non calculé"


def test_contradictory_grades_are_not_computed():
    sheet = grades(15, 12, 12) + [{"matiere": "SVT", "note": 9}]
    assert compute_ranking_average("D", MEDECINE_SUBJECTS, sheet)["status"] == "non calculé"


def test_unsupported_serie_and_unknown_subject_are_not_computed():
    assert compute_ranking_average("A1", MEDECINE_SUBJECTS, grades(15, 12, 12))["status"] == "non calculé"
    assert compute_ranking_average("D", ["Couture"], grades(15, 12, 12))["status"] == "non calculé"


def test_offer_without_subjects_is_not_computed():
    assert compute_ranking_average("D", [], grades(15, 12, 12))["status"] == "non calculé"


@pytest.mark.parametrize("subjects", [["SVT", "SVT", "Maths", "PCT"], ["SVT", "Maths", "Mathématiques", "PCT"]])
def test_duplicate_offer_subject_is_not_computed(subjects):
    result = compute_ranking_average("D", subjects, grades(15, 12, 12))
    assert result["status"] == "non calculé"
    assert result["reason"].startswith("matière en double")


def test_grade_flagged_unreadable_is_not_computed_even_with_a_note():
    sheet = grades(15, 12, 12)
    sheet[0]["lisible"] = False
    assert compute_ranking_average("D", MEDECINE_SUBJECTS, sheet) == {
        "status": "non calculé", "reason": "note illisible: SVT"}


@pytest.mark.parametrize("sheet", [None, [None], [{"note": 12}]])
def test_malformed_grades_are_not_computed(sheet):
    assert compute_ranking_average("D", MEDECINE_SUBJECTS, sheet)["status"] == "non calculé"


def test_display_rounding_is_two_decimals_half_up():
    sheet = [{"matiere": "Philosophie", "note": 10.01}, {"matiere": "Français", "note": 10}]
    result = compute_ranking_average("D", ["Philosophie", "Français"], sheet)
    assert result["moyenne_arrondie"] == 10.01  # exact value 10.005
