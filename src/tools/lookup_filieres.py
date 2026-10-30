"""Filter the guide offers accessible to a serie, then rank them (E3.5).

Access is strict and deterministic (docs/prd.md section 3.1): an offer is
accessible only when its row has Statut_qualité = OK, the serie appears in
Bac_recommandé (or the row is open to all series), and its page of the
official PDF is established. Ranking is soft and explained (section 3.2):
the metier_vise and the interets are matched as whole words against
Débouchés_Métiers and Filière, and the ranking average is computed by
compute_ranking_average when grades are given, never for a Concours.

Returns {"accessible": [...], "excluded": [...]}: the excluded rows are
the ones open to the serie that strict access rejected, with the reason
and their Statut_qualité, for the "Ce que je n'ai pas pu vérifier"
section. No city and no admission chance is ever produced: the guide
publishes neither. Pure code: no network, no SDK.
"""

import re
import unicodedata

from src.domain.guide import NOT_PUBLISHED, OK_STATUS, load_offer_rows, load_pages_by_id
from src.domain.offer_subjects import ALL_SERIES_HEADER, STATUS_CONCOURS, subjects_for_serie
from src.tools.compute_ranking_average import compute_ranking_average

MAX_ACCESSIBLE = 5  # docs/prd.md section 3.2: the report shows at most 5 offers
CONCOURS_NOTE = "les notes du Bac ne suffisent pas"  # docs/prd.md section 3.1, Concours entry
MODE_NOT_PUBLISHED_REASON = "mode d'entrée non publié par le guide"  # dash cell, page 86/87/89
_STOPWORDS = {"de", "des", "du", "la", "le", "les", "en", "et", "d", "au", "aux", "un", "une"}
# Ranking weights only order the accessible offers (PRD section 3.2 lists
# metier, then interets, then the average): a metier match in the careers
# outweighs one in the program name, which outweighs a single interest.
_SCORE_METIER_DEBOUCHES = 100
_SCORE_METIER_FILIERE = 50
_SCORE_INTERET = 20


def lookup_filieres(serie: str | None = None, metier_vise: str | None = None,
                    interets: list[str] | str | None = None,
                    grades: list[dict] | None = None) -> dict:
    """Return {"accessible", "excluded"} for `serie`, ranked and explained.

    `metier_vise` and each of `interets` are phrases matched as whole
    words (accents and case ignored). When grades are given, each
    Classement offer also carries its ranking average; a Concours offer
    never does. A missing serie raises ValueError: asking, not guessing.
    """
    if not isinstance(serie, str) or not serie.strip():
        raise ValueError("serie is required: asking, not guessing")
    serie = serie.strip()
    pages = load_pages_by_id()
    accessible, excluded = [], []
    for row in load_offer_rows():
        failures = _access_failures(row, serie, pages)
        if failures:
            if _is_open_to_serie(row, serie) or _bac_is_unpublished(row):
                excluded.append(_excluded_entry(row, pages, failures))
            continue
        entry = _accessible_entry(row, serie, pages, metier_vise, interets, grades)
        if entry is not None:
            accessible.append(entry)
    accessible.sort(key=lambda offer: (-offer["score"],
                                       -(offer["moyenne_classement"] or -1),
                                       offer["Offre_ID"]))
    return {"accessible": accessible[:MAX_ACCESSIBLE],
            "excluded": sorted(excluded, key=lambda offer: offer["Offre_ID"])}


def _access_failures(row: dict, serie: str, pages: dict) -> list[str]:
    failures = []
    if row.get("Statut_qualité") != OK_STATUS:
        failures.append(f"Statut_qualité = {row.get('Statut_qualité')} "
                        f"(seules les lignes {OK_STATUS} sont recommandées)")
    if row.get("Bac_recommandé", "").strip() == NOT_PUBLISHED:
        failures.append("Bac_recommandé non publié par le guide : série non vérifiable")
    elif not _is_open_to_serie(row, serie):
        failures.append(f"série {serie} absente de Bac_recommandé")
    if row.get("Offre_ID") not in pages:
        failures.append("page du guide non établie")
    return failures


def _is_open_to_serie(row: dict, serie: str) -> bool:
    values = [value.strip() for value in row.get("Bac_recommandé", "").split(",")]
    return serie in values or any(value.startswith(ALL_SERIES_HEADER) for value in values)


def _bac_is_unpublished(row: dict) -> bool:
    return row.get("Bac_recommandé", "").strip() == NOT_PUBLISHED


def _accessible_entry(row: dict, serie: str, pages: dict, metier_vise: str | None,
                      interets: list[str] | str | None, grades: list[dict] | None) -> dict | None:
    score, raisons = _ranking_reasons(row, metier_vise, interets)
    if (metier_vise or interets) and score == 0:
        return None  # no whole-word match: not a recommendation for this student
    entry = _base_entry(row, pages)
    entry["raisons"] = _access_reasons(row, serie, pages) + raisons
    entry["score"] = score
    entry.update(_average_fields(row, serie, grades, entry))
    return entry


def _average_fields(row: dict, serie: str, grades: list[dict] | None, entry: dict) -> dict:
    subjects = subjects_for_serie(row, serie)
    if subjects["status"] == STATUS_CONCOURS or row.get("Mode_entrée") == "Concours":
        entry["raisons"].append(f"Concours : {CONCOURS_NOTE}, admission par épreuve séparée")
        return {"moyenne_classement": None, "calcul": None,
                "epreuves": subjects["epreuves"]}
    if row.get("Mode_entrée", "").strip() == NOT_PUBLISHED:
        # A ranking average would imply admission by ranking, which the
        # guide does not state for these rows (dash cell, audit E3.3).
        return {"moyenne_classement": None, "calcul": None, "epreuves": [],
                "calcul_non_fait": MODE_NOT_PUBLISHED_REASON}
    if grades is None:
        return {"moyenne_classement": None, "calcul": None, "epreuves": []}
    if subjects["status"] != "calculable":
        return {"moyenne_classement": None, "calcul": None, "epreuves": [],
                "calcul_non_fait": subjects["reason"]}
    result = compute_ranking_average(serie, subjects["subjects"], grades)
    if result.get("status") != "calculé":
        return {"moyenne_classement": None, "calcul": None, "epreuves": [],
                "calcul_non_fait": result.get("reason")}
    entry["raisons"].append(
        f"moyenne de classement {result['moyenne_arrondie']} calculée sur "
        f"{', '.join(subjects['subjects'])}")
    return {"moyenne_classement": result["moyenne_arrondie"], "calcul": result,
            "epreuves": []}


def _base_entry(row: dict, pages: dict) -> dict:
    page = pages.get(row["Offre_ID"])
    return {"Offre_ID": row["Offre_ID"], "Filière": row.get("Filière", ""),
            "Établissement": row.get("Établissement", ""),
            "page_pdf": int(page) if page else None,
            "Mode_entrée": row.get("Mode_entrée", ""),
            "Bac_recommandé": row.get("Bac_recommandé", ""),
            "Statut_qualité": row.get("Statut_qualité", ""),
            "Bourse": row.get("Bourse", ""), "Aide_FPP": row.get("Aide_FPP", ""),
            "Débouchés_Métiers": row.get("Débouchés_Métiers", "")}


def _access_reasons(row: dict, serie: str, pages: dict) -> list[str]:
    raisons = [f"série {serie} dans Bac_recommandé ({row.get('Bac_recommandé')})",
               f"Statut_qualité = {OK_STATUS}",
               f"page {pages[row['Offre_ID']]} du guide officiel",
               f"Mode d'entrée : {row.get('Mode_entrée')}"]
    for champ in ("Bourse", "Aide_FPP"):
        if row.get(champ, "").strip() == NOT_PUBLISHED:
            raisons.append(f"{champ} : {NOT_PUBLISHED} par le guide")
    return raisons


def _excluded_entry(row: dict, pages: dict, failures: list[str]) -> dict:
    entry = _base_entry(row, pages)
    entry["raisons"] = failures
    return entry


def _ranking_reasons(row: dict, metier_vise: str | None,
                     interets: list[str] | str | None) -> tuple[int, list[str]]:
    score, raisons = 0, []
    if metier_vise:
        if _phrase_matches(metier_vise, row.get("Débouchés_Métiers", "")):
            score += _SCORE_METIER_DEBOUCHES
            raisons.append(f"métier visé « {metier_vise} » retrouvé comme mots entiers "
                           f"dans Débouchés_Métiers")
        if _phrase_matches(metier_vise, row.get("Filière", "")):
            score += _SCORE_METIER_FILIERE
            raisons.append(f"métier visé « {metier_vise} » retrouvé comme mots entiers "
                           f"dans Filière")
    for interet in _as_phrases(interets):
        if _phrase_matches(interet, row.get("Débouchés_Métiers", "")) \
                or _phrase_matches(interet, row.get("Filière", "")):
            score += _SCORE_INTERET
            raisons.append(f"intérêt « {interet} » retrouvé comme mots entiers "
                           f"dans Filière ou Débouchés_Métiers")
    return score, raisons


def _as_phrases(interets: list[str] | str | None) -> list[str]:
    if not interets:
        return []
    return [interets] if isinstance(interets, str) else list(interets)


def _phrase_matches(phrase: str, text: str) -> bool:
    """True when every meaningful word of `phrase` is a whole word of `text`.

    Whole words only, never substrings: "pilote de ligne" needs both
    "pilote" and "ligne", so the drone operator of Foresterie Tropicale
    does not match (docs/prd.md section 3.2, case false_friend).
    """
    words = [word for word in _words(phrase) if word not in _STOPWORDS]
    if not words:
        return False
    text_words = set(_words(text))
    return all(word in text_words for word in words)


def _words(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFD", str(text).casefold())
    folded = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.findall(r"[a-z0-9]+", folded)
