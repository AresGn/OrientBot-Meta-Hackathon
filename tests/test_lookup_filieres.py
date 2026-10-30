"""Rewritten lookup_filieres (E3.5, issue #24).

Strict access first (Statut_qualité = OK, serie in Bac_recommandé, page
established), then whole-word ranking by metier_vise / interets, with the
excluded rows returned alongside. Deterministic: no network, no API key.
Cases named from docs/prd.md section 10: unverified_trap, false_friend,
concours_entry, clear_sheet_d_medecin.
"""

import pytest

from src.domain.guide import NOT_PUBLISHED, load_offer_rows, load_pages_by_id
from src.tools.lookup_filieres import MAX_ACCESSIBLE, lookup_filieres

GRADES_D = [{"matiere": "SVT", "note": 15, "lisible": True},
            {"matiere": "Mathématiques", "note": 12, "lisible": True},
            {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12, "lisible": True}]


def accessible_ids(result):
    return [offer["Offre_ID"] for offer in result["accessible"]]


def excluded_ids(result):
    return [offer["Offre_ID"] for offer in result["excluded"]]


def test_returns_accessible_and_excluded_with_proof_fields():
    result = lookup_filieres(serie="D", metier_vise="médecin")
    assert set(result) == {"accessible", "excluded"}
    for offer in result["accessible"] + result["excluded"]:
        assert offer["Offre_ID"]
        assert "page_pdf" in offer
        assert offer["Mode_entrée"]
        assert offer["raisons"]


def test_access_is_strict_ok_serie_and_established_page():
    result = lookup_filieres(serie="D")
    pages = load_pages_by_id()
    for offer in result["accessible"]:
        assert offer["Statut_qualité"] == "OK"
        assert offer["Offre_ID"] in pages
        assert offer["page_pdf"] == int(pages[offer["Offre_ID"]])
        assert "D" in [s.strip() for s in offer["Bac_recommandé"].split(",")] \
            or offer["Bac_recommandé"].startswith("Toutes séries")


def test_medecin_ranks_pub_062_and_pub_133_first():
    result = lookup_filieres(serie="D", metier_vise="médecin", grades=GRADES_D)
    assert accessible_ids(result)[:2] == ["PUB-062", "PUB-133"]
    medecine = result["accessible"][0]
    assert medecine["page_pdf"] == 36
    assert medecine["moyenne_classement"] == 13.15
    assert any("médecin" in raison for raison in medecine["raisons"])


def test_unverified_trap_pub_064_is_excluded_with_its_status():
    result = lookup_filieres(serie="D", metier_vise="pharmacien")
    assert "PUB-064" not in accessible_ids(result)
    excluded = {offer["Offre_ID"]: offer for offer in result["excluded"]}
    assert excluded["PUB-064"]["Statut_qualité"] == "Réparé - fusion OCR"
    assert any("Réparé - fusion OCR" in raison
               for raison in excluded["PUB-064"]["raisons"])


def test_false_friend_pilote_de_ligne_returns_no_foresterie():
    result = lookup_filieres(serie="D", metier_vise="pilote de ligne")
    assert result["accessible"] == []
    assert "PUB-200" not in accessible_ids(result)
    assert all("Foresterie" not in offer["Filière"]
               for offer in result["accessible"])


def test_pilote_alone_does_not_rank_foresterie_by_substring():
    result = lookup_filieres(serie="D", metier_vise="pilote")
    assert "PUB-200" not in accessible_ids(result)


def test_concours_entry_is_marked_and_no_average_is_computed():
    result = lookup_filieres(serie="D", metier_vise="infirmier", grades=GRADES_D)
    assert result["accessible"]
    for offer in result["accessible"]:
        assert offer["Mode_entrée"] == "Concours"
        assert offer["moyenne_classement"] is None
        assert offer["calcul"] is None
        assert any("les notes du Bac ne suffisent pas" in raison
                   for raison in offer["raisons"])


def test_at_most_five_accessible_and_no_ville_or_admission_chance():
    result = lookup_filieres(serie="D")
    assert 0 < len(result["accessible"]) <= MAX_ACCESSIBLE == 5
    for offer in result["accessible"]:
        assert offer["raisons"]
        lowered = str(offer).casefold()
        assert "ville" not in lowered
        assert "probabilité" not in lowered
        assert "chance d'admission" not in lowered


def test_whole_word_matching_ignores_accents_and_case():
    result = lookup_filieres(serie="D", metier_vise="MEDECIN")
    assert accessible_ids(result)[:2] == ["PUB-062", "PUB-133"]


def test_interets_match_whole_words_in_filiere_or_debouches():
    result = lookup_filieres(serie="D", interets=["biologie"])
    assert result["accessible"]
    assert all(offer["score"] > 0 for offer in result["accessible"])


def test_missing_serie_asks_rather_than_guesses():
    with pytest.raises(ValueError):
        lookup_filieres(serie="")
    with pytest.raises(ValueError):
        lookup_filieres(serie=None)


def test_non_published_quotas_are_never_presented_as_zero():
    result = lookup_filieres(serie="D", metier_vise="entrepreneur")
    for offer in result["accessible"]:
        if offer["Offre_ID"] in {"PUB-211", "PUB-212", "PUB-213", "PUB-214", "PUB-215"}:
            assert offer["Bourse"] == NOT_PUBLISHED
            assert any(NOT_PUBLISHED in raison for raison in offer["raisons"])


def test_data_repairs_from_the_audit_are_applied():
    rows = {row["Offre_ID"]: row for row in load_offer_rows()}
    pages = load_pages_by_id()
    assert rows["PUB-025"]["Établissement"] == "Ecole Normale Supérieure /Porto-Novo"
    assert rows["PUB-045"]["Établissement"].endswith("(FLASH-Adjarra)")
    assert rows["PUB-048"]["Établissement"].endswith("(FLLAC)")
    assert rows["PUB-142"]["Établissement"].endswith("(FLASH)")
    for offre_id in ("PUB-186", "PUB-187", "PUB-188"):
        assert rows[offre_id]["Établissement"].endswith("(INSTI)")
    for offre_id in ("PUB-053", "PUB-054", "PUB-055"):
        assert rows[offre_id]["Établissement"] == "Faculté des Sciences Agronomiques (FSA)"
    assert rows["PUB-130"]["Établissement"] == \
        "Faculté de Droit et Sciences Politiques (FDSP)"
    assert rows["PUB-141"]["Établissement"] == \
        "Faculté des Lettres, Arts et Sciences Humaines (FLASH)"
    for offre_id, page in (("PUB-025", "42"), ("PUB-045", "23"), ("PUB-048", "24"),
                           ("PUB-142", "53"), ("PUB-186", "57"), ("PUB-187", "59"),
                           ("PUB-188", "58")):
        assert pages[offre_id] == page, offre_id
    assert "des équipements" in rows["PUB-032"]["Débouchés_Métiers"]
    assert "et vétérinaires" in rows["PUB-032"]["Débouchés_Métiers"]
    assert "DEAT" in rows["PUB-211"]["Bac_recommandé"]
    assert "EA" in rows["PUB-211"]["Bac_recommandé"]
    assert "DEAT" in rows["PUB-211"]["Matières"]
    assert rows["PUB-189"]["Filière"] == \
        "Génie Énergétique (Énergies Renouvelables et Systèmes Énergétiques)"
    for offre_id in ("PUB-211", "PUB-212", "PUB-213", "PUB-214", "PUB-215",
                     "PUB-217", "PUB-218"):
        assert rows[offre_id]["Bourse"] == NOT_PUBLISHED, offre_id
        assert rows[offre_id]["Aide_FPP"] == NOT_PUBLISHED, offre_id
    # True zeros published by the guide stay zero (page 45, page 54, page 56).
    for offre_id in ("PUB-085", "PUB-086", "PUB-145", "PUB-180"):
        assert rows[offre_id]["Bourse"] == "0", offre_id
