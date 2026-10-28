import pytest

from src.domain.grade_scale import MAX_GRADE, MIN_GRADE, is_on_grade_scale


@pytest.mark.parametrize("value", [MIN_GRADE, 9.5, MAX_GRADE])
def test_bounds_are_on_the_scale(value):
    assert is_on_grade_scale(value)


@pytest.mark.parametrize("value", [-0.5, 20.5, float("nan")])
def test_values_outside_0_20_are_off_the_scale(value):
    assert not is_on_grade_scale(value)
