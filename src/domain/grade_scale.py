MIN_GRADE = 0  # grade scale of the Bac
MAX_GRADE = 20


def is_on_grade_scale(value: float) -> bool:
    """True for a grade or average within the Bac's 0-20 scale, bounds included."""
    return MIN_GRADE <= value <= MAX_GRADE
