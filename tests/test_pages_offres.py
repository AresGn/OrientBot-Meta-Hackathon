"""Schema and behavior of data/pages_offres.csv (E3.2, issue #21).

Every filiere proof points at the page of the official guide: this file locks
the finished mapping (no a_verifier left, the two missing offers resolved,
7 offers with an unconfirmed établissement quarantined as page_non_etablie)
and proves that an offer without a page cannot produce a filiere proof,
so it is never recommended.
"""

import csv

from src.domain.guide import PAGE_NON_ETABLIE, PAGES_PATH, load_offer_rows, load_pages_by_id
from src.tools.verify_report import verify_report
from src.vertical_slice import run_vertical_slice

# issue #21: the only page_statut values once the draft is finished,
# written out so the test cannot pass by following the code constant.
ALLOWED_STATUSES = {"unique", "sigle", "verifie_main", "page_non_etablie"}

# The a_verifier rows whose page the PDF confirms with a matching
# establishment, checked by hand against the local PDF (data/source/,
# never committed); 7 confirmed, 5 corrected (006: 32 -> 33,
# 027/028/030 -> 42, 189: 57 -> 58). See docs/decisions.md.
MANUALLY_VERIFIED_PAGES = {
    "PUB-006": 33, "PUB-027": 42, "PUB-028": 42, "PUB-030": 42,
    "PUB-043": 42, "PUB-064": 36, "PUB-066": 43, "PUB-071": 31,
    "PUB-110": 40, "PUB-171": 56, "PUB-175": 56, "PUB-189": 58,
}

# The 7 a_verifier rows whose PDF row contradicts the CSV establishment:
# quarantined as page_non_etablie until E3.3 fixes the labels. The pages
# found (025: 42, 045: 23, 048: 24, 142: 53, 186: 57, 187: 59, 188: 58)
# are recorded in docs/decisions.md for restoration after E3.3.
NON_ETABLIE_OFFERS = ("PUB-025", "PUB-045", "PUB-048", "PUB-142",
                      "PUB-186", "PUB-187", "PUB-188")

# The 2 introuvable rows, both found in the PDF: ENATSE on page 48,
# the UADC cooperative row on page 86.
RESOLVED_MISSING_PAGES = {"PUB-122": 48, "PUB-210": 86}

# 5 sigle rows drawn at random (seed 21, the issue number) and rechecked
# against the PDF; their pages were confirmed unchanged.
RECHECKED_SIGLE_PAGES = {
    "PUB-047": 23, "PUB-068": 31, "PUB-090": 26, "PUB-174": 57, "PUB-185": 64,
}


def load_page_rows():
    with PAGES_PATH.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def test_page_statut_values_are_limited_to_the_four_allowed():
    rows = load_page_rows()
    assert rows
    assert {row["page_statut"] for row in rows} <= ALLOWED_STATUSES


def test_no_a_verifier_row_is_left():
    rows = load_page_rows()
    assert [row["Offre_ID"] for row in rows if row["page_statut"] == "a_verifier"] == []


def test_pub_064_points_to_page_36():
    rows = {row["Offre_ID"]: row for row in load_page_rows()}
    assert rows["PUB-064"]["page_pdf"] == "36"


def test_pub_122_and_210_have_a_page_or_are_page_non_etablie():
    rows = {row["Offre_ID"]: row for row in load_page_rows()}
    for offre_id in ("PUB-122", "PUB-210"):
        row = rows[offre_id]
        if row["page_statut"] == PAGE_NON_ETABLIE:
            assert row["page_pdf"] == ""
        else:
            assert int(row["page_pdf"]) >= 1


def test_formerly_missing_offers_are_resolved_with_a_page():
    rows = {row["Offre_ID"]: row for row in load_page_rows()}
    assert len(RESOLVED_MISSING_PAGES) == 2
    for offre_id, page in RESOLVED_MISSING_PAGES.items():
        assert rows[offre_id]["page_statut"] == "verifie_main", offre_id
        assert rows[offre_id]["page_pdf"] == str(page), offre_id


def test_offers_with_unconfirmed_etablissement_are_page_non_etablie():
    rows = {row["Offre_ID"]: row for row in load_page_rows()}
    assert len(NON_ETABLIE_OFFERS) == 7
    for offre_id in NON_ETABLIE_OFFERS:
        assert rows[offre_id]["page_statut"] == PAGE_NON_ETABLIE, offre_id
        assert rows[offre_id]["page_pdf"] == "", offre_id
    assert [offre_id for offre_id, row in rows.items()
            if row["page_statut"] == PAGE_NON_ETABLIE] == list(NON_ETABLIE_OFFERS)


def test_every_offer_has_a_page_row():
    offer_ids = [row["Offre_ID"] for row in load_offer_rows()]
    page_ids = [row["Offre_ID"] for row in load_page_rows()]
    assert len(offer_ids) == 224
    assert sorted(page_ids) == sorted(offer_ids)


def test_page_pdf_is_a_positive_integer_unless_page_non_etablie():
    for row in load_page_rows():
        if row["page_statut"] == PAGE_NON_ETABLIE:
            assert row["page_pdf"] == "", row["Offre_ID"]
        else:
            assert int(row["page_pdf"]) >= 1, row["Offre_ID"]


def test_manually_verified_pages_match_the_pdf_check():
    rows = {row["Offre_ID"]: row for row in load_page_rows()}
    assert len(MANUALLY_VERIFIED_PAGES) == 12
    for offre_id, page in MANUALLY_VERIFIED_PAGES.items():
        assert rows[offre_id]["page_statut"] == "verifie_main", offre_id
        assert rows[offre_id]["page_pdf"] == str(page), offre_id


def test_five_sigle_rows_were_rechecked():
    rows = {row["Offre_ID"]: row for row in load_page_rows()}
    assert len(RECHECKED_SIGLE_PAGES) == 5
    for offre_id, page in RECHECKED_SIGLE_PAGES.items():
        assert rows[offre_id]["page_statut"] == "sigle", offre_id
        assert rows[offre_id]["page_pdf"] == str(page), offre_id


def test_page_index_lists_exactly_the_offers_with_a_page():
    rows = {row["Offre_ID"]: row for row in load_page_rows()}
    pages = load_pages_by_id()
    assert set(pages) == {offre_id for offre_id, row in rows.items()
                          if row["page_pdf"]}
    assert all(pages[offre_id] == rows[offre_id]["page_pdf"] for offre_id in pages)
    assert pages["PUB-062"] == "36"
    assert pages["PUB-122"] == "48"
    for offre_id in NON_ETABLIE_OFFERS:
        assert offre_id not in pages, offre_id


def test_offer_without_page_cannot_produce_a_filiere_proof():
    # PUB-186 is Statut_qualité = OK with Bourse = 50: champ and valeur are
    # right and 57 is the page found, so only the missing index entry,
    # quarantined until E3.3 fixes the établissement, can refuse this proof.
    report = {"schema_version": 1,
              "claims": [{"claim_id": "genie-civil",
                          "text": "Génie Civil : bourses prévues.",
                          "proofs": [{"type": "filiere", "offre_id": "PUB-186",
                                      "page_pdf": 57, "champ": "Bourse",
                                      "valeur": 50}]}]}
    context = {"serie": "D", "grades": [], "transcript": ""}
    problems = verify_report(report, context)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("genie-civil", "filiere")]


def test_offer_with_established_page_is_recommended_by_the_slice():
    # PUB-122 was page-less, hence skipped; its page 48 established, the
    # calculable ENATSE offer joins the verified report like PUB-121.
    fixture = {
        "serie": "D",
        "grades": [{"matiere": "Anglais", "note": 8, "lisible": True},
                   {"matiere": "Mathématiques", "note": 12, "lisible": True},
                   {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12,
                    "lisible": True},
                   {"matiere": "SVT", "note": 15, "lisible": True}],
        "transcript": "je suis en série D, la santé publique m'intéresse",
        "profile": {"metier_vise": {"value": "santé publique",
                                    "quote": "santé publique"}},
    }
    result = run_vertical_slice(fixture)
    assert result["problems"] == []
    assert "PUB-121" in result["text"]
    assert "PUB-122" in result["text"]
