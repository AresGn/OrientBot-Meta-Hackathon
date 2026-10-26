import csv

from src.tools import lookup_filieres as mod


def test_todo_rows_are_excluded():
    assert mod.lookup_filieres() == []


def test_only_verified_rows_are_returned(tmp_path, monkeypatch):
    path = tmp_path / "f.csv"
    header = ["filiere", "etablissement", "serie_bac_requise", "condition_acces", "source_url", "source_status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(["A", "X", "C", "c", "https://example.org/a", "verifie"])
        w.writerow(["B", "Y", "C", "c", "TODO", "TODO"])
    monkeypatch.setattr(mod, "DATA", path)
    assert [r["filiere"] for r in mod.lookup_filieres("C")] == ["A"]
