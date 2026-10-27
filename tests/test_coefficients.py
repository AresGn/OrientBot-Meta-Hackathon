import pytest

from src.domain.coefficients import UnknownSerieError, load_coefficients


def test_serie_d_coefficients_come_from_the_json():
    assert load_coefficients("D") == {
        "SVT": 5, "Mathématiques": 4, "Sciences Physiques (PCT/SPCT)": 4, "Philosophie": 2,
        "Français": 2, "Anglais": 2, "Histoire-Géographie": 2,
    }


def test_serie_c_coefficients_come_from_the_json():
    coefficients = load_coefficients("C")
    assert coefficients["Mathématiques"] == 6
    assert coefficients["Sciences Physiques (PCT/SPCT)"] == 5
    assert coefficients["SVT"] == 2


def test_eps_and_oral_subjects_are_not_ranking_subjects():
    for serie in ("C", "D"):
        assert sum(load_coefficients(serie).values()) == 21  # 22 official total minus EPS 1
        assert "EPS" not in load_coefficients(serie)


@pytest.mark.parametrize("serie", ["A1", "B", "", None])
def test_unsupported_serie_raises_explicit_error(serie):
    with pytest.raises(UnknownSerieError):
        load_coefficients(serie)
