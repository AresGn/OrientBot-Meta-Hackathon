"""Repair the guide CSVs for E3.5 (issue #24), traced in docs/data-audit.md.

Every value below was checked by hand against the local PDF
(data/source/guide_2026.pdf, never committed) at the page given in
docs/data-audit.md: the 7 quarantined etablissements (E3.2) and their
pages, the 5 FSA/FDSP/FLASH labels (E3.4), PUB-032's glued words,
PUB-211's DEAT/EA series and DEAT segment, PUB-189's missing filiere,
and the dash cells of the 0/0 rows, which become the "non publié"
marker instead of an invented 0 (true published zeros stay 0).

Idempotent: a value already repaired is left alone; a value that is
neither the known old value nor the repaired one aborts the script,
so a new extraction is never masked silently. data/ is written only
through this script (AGENTS.md).

Usage (from the repository root):

    python scripts/repair_guide_data_e35.py
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.guide import NOT_PUBLISHED  # noqa: E402

OFFERS_PATH = ROOT / "data" / "offres_publiques_2026_2027.csv"
PAGES_PATH = ROOT / "data" / "pages_offres.csv"

INSTI = "Institut National Supérieur de Technologie Industrielle (INSTI)"
FSA = "Faculté des Sciences Agronomiques (FSA)"  # PDF pages 35/36 for PUB-053/054/055
FLASH = "Faculté des Lettres, Arts et Sciences Humaines (FLASH)"  # PDF page 53

ETABLISSEMENT_REPAIRS = {
    "PUB-025": "Ecole Normale Supérieure /Porto-Novo",  # PDF page 42, ENS (was ENSTIC)
    "PUB-045": "Faculté des Lettres, Arts et Sciences Humaines-Adjarra (FLASH-Adjarra)",  # p. 23
    "PUB-048": "Faculté des Lettres, Langues, Arts et Communications (FLLAC)",  # page 24
    "PUB-053": FSA, "PUB-054": FSA, "PUB-055": FSA,
    "PUB-130": "Faculté de Droit et Sciences Politiques (FDSP)",  # PDF page 53
    "PUB-141": FLASH, "PUB-142": FLASH,  # PDF page 53
    "PUB-186": INSTI, "PUB-187": INSTI, "PUB-188": INSTI,  # PDF pages 57, 59, 58
}
PAGE_REPAIRS = {"PUB-025": "42", "PUB-045": "23", "PUB-048": "24", "PUB-142": "53",
                "PUB-186": "57", "PUB-187": "59", "PUB-188": "58"}  # docs/data-audit.md, E3.2
PUB_032_FIXES = {"deséquipements": "des équipements", "etvétérinaires": "et vétérinaires",
                 "équipementsélectroniques": "équipements électroniques"}  # PDF page 39
PUB_189_FILIERE = "Génie Énergétique (Énergies Renouvelables et Systèmes Énergétiques)"  # p. 58
PUB_211_BAC = "A1, A2, B, C, D, G2, G3, DEAT, EA"  # PDF page 86: DEAT and EA were omitted
PUB_211_MATIERES_SUFFIX = " DEAT : Les trois (03) matières écrites"  # PDF page 86
# Dash quotas (and entry mode) on pages 86/87/89: UADC and Seme City rows.
QUOTA_NOT_PUBLISHED = ("PUB-211", "PUB-212", "PUB-213", "PUB-214", "PUB-215",
                       "PUB-217", "PUB-218")
# Published 0/0 quotas but a dash entry mode on page 45: Institut Confucius, ILACI.
MODE_NOT_PUBLISHED = ("PUB-085", "PUB-086", "PUB-096", "PUB-097", "PUB-098", "PUB-099")
BAC_NOT_PUBLISHED = ("PUB-217", "PUB-218", "PUB-219")  # pages 89 and 84: dash, not Toutes séries


# The value each repaired etablissement carried before E3.5 (main, before
# this script): _set aborts on anything else, so a new extraction with a
# different label is never overwritten silently.
ETABLISSEMENT_OLD = {
    "PUB-025": "Ecole Nationale des Sciences et Techniques de l'Information et de la Communication (ENSTIC)",
    "PUB-045": "Faculté de Droit et de Science Politique (FADESP)",
    "PUB-048": "Faculté des Lettres, Arts et Sciences Humaines-Adjarra (FLASH-Adjarra)",
    "PUB-053": "Faculté des Lettres, Langues, Arts et Communications (FLLAC)",
    "PUB-054": "Faculté des Lettres, Langues, Arts et Communications (FLLAC)",
    "PUB-055": "Faculté des Lettres, Langues, Arts et Communications (FLLAC)",
    "PUB-130": "Faculté d'Agronomie(FA)",
    "PUB-141": "Faculté de Sciences Economiques et de Gestion (FASEG)",
    "PUB-142": "Faculté de Sciences Economiques et de Gestion (FASEG)",
    "PUB-186": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
    "PUB-187": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
    "PUB-188": "Faculté des Sciences et Techniques de Natitingou (FAST/Natitingou)",
}
PUB_032_OLD = ("Technicien de laboratoire des centres de santé,Maintenance hospitalière et "
               "contrôle deséquipements de laboratoires médicaux etvétérinaires, "
               "Maintenance des équipementsélectroniques")
PUB_211_BAC_OLD = "A1, A2, B, C, D, G2, G3"
PUB_211_MATIERES_OLD = ("A1, A2, B : Anglais, Français, Hist-GéoC, D : Anglais, Français, "
                        "MathsG2, G3 : Anglais, Etude de Cas, Français")
QUOTA_OLD = {"Bourse": "0", "Aide_FPP": "0", "Total_allocations": "0"}
MODE_OLD = {**{offre_id: "Classement" for offre_id in
               ("PUB-211", "PUB-212", "PUB-213", "PUB-214", "PUB-215")},
            **{offre_id: "Dossier" for offre_id in ("PUB-217", "PUB-218")}}


def _set(row: dict, champ: str, new: str, changes: list[str],
         expected_old: str | None = None) -> None:
    """Set one repaired value, aborting on an unexpected current value.

    Already repaired: left alone. Equal to `expected_old` (when given):
    repaired and logged. Anything else: ValueError, nothing is masked.
    """
    if row[champ] == new:
        return
    if expected_old is not None and row[champ] != expected_old:
        raise ValueError(f"{row['Offre_ID']} {champ}: unexpected value {row[champ]!r}, "
                         f"expected the known old value {expected_old!r} or {new!r}; "
                         f"aborting, nothing overwritten")
    changes.append(f"{row['Offre_ID']} {champ}: {row[champ]!r} -> {new!r}")
    row[champ] = new


def repair_offer_rows(rows: list[dict]) -> list[str]:
    """Apply the traced repairs to the offer rows; return the change log."""
    changes: list[str] = []
    by_id = {row["Offre_ID"]: row for row in rows}
    for offre_id, label in ETABLISSEMENT_REPAIRS.items():
        _set(by_id[offre_id], "Établissement", label, changes,
             expected_old=ETABLISSEMENT_OLD[offre_id])
    debouches = by_id["PUB-032"]["Débouchés_Métiers"]
    for glued, fixed in PUB_032_FIXES.items():
        debouches = debouches.replace(glued, fixed)
    _set(by_id["PUB-032"], "Débouchés_Métiers", debouches, changes,
         expected_old=PUB_032_OLD)
    _set(by_id["PUB-189"], "Filière", PUB_189_FILIERE, changes, expected_old="")
    _set(by_id["PUB-211"], "Bac_recommandé", PUB_211_BAC, changes,
         expected_old=PUB_211_BAC_OLD)
    _set(by_id["PUB-211"], "Matières", PUB_211_MATIERES_OLD + PUB_211_MATIERES_SUFFIX,
         changes, expected_old=PUB_211_MATIERES_OLD)
    for offre_id in QUOTA_NOT_PUBLISHED:
        for champ in ("Bourse", "Aide_FPP", "Total_allocations"):
            _set(by_id[offre_id], champ, NOT_PUBLISHED, changes,
                 expected_old=QUOTA_OLD[champ])
        _set(by_id[offre_id], "Mode_entrée", NOT_PUBLISHED, changes,
             expected_old=MODE_OLD[offre_id])
    for offre_id in MODE_NOT_PUBLISHED:
        _set(by_id[offre_id], "Mode_entrée", NOT_PUBLISHED, changes,
             expected_old="Classement")
    for offre_id in BAC_NOT_PUBLISHED:
        _set(by_id[offre_id], "Bac_recommandé", NOT_PUBLISHED, changes,
             expected_old="Toutes séries")
    return changes


def repair_page_rows(rows: list[dict]) -> list[str]:
    """Restore the 7 quarantined pages as verifie_main; return the change log."""
    changes: list[str] = []
    by_id = {row["Offre_ID"]: row for row in rows}
    for offre_id, page in PAGE_REPAIRS.items():
        _set(by_id[offre_id], "page_pdf", page, changes, expected_old="")
        _set(by_id[offre_id], "page_statut", "verifie_main", changes,
             expected_old="page_non_etablie")
    return changes


def _read(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def _write(path: Path, fieldnames: list[str], rows: list[dict], bom: bool,
           lineterminator: str) -> None:
    encoding = "utf-8-sig" if bom else "utf-8"  # offres carries a BOM, pages_offres does not
    # Each file keeps its committed line terminator (offres CRLF, pages LF):
    # writing CRLF into pages_offres rewrote all 225 lines on a no-op rerun.
    with path.open("w", newline="", encoding=encoding) as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator=lineterminator)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    offer_fields, offer_rows = _read(OFFERS_PATH)
    page_fields, page_rows = _read(PAGES_PATH)
    changes = repair_offer_rows(offer_rows) + repair_page_rows(page_rows)
    _write(OFFERS_PATH, offer_fields, offer_rows, bom=True, lineterminator="\r\n")
    _write(PAGES_PATH, page_fields, page_rows, bom=False, lineterminator="\n")
    for change in changes:
        print(change)
    print(f"{len(changes)} repair(s) applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
