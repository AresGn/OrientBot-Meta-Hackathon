from src.tools.lookup_filieres import lookup_filieres


def test_unverified_rows_are_excluded():
    assert lookup_filieres() == []
