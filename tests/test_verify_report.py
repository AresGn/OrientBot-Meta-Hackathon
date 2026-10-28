import copy

import pytest

from src.tools import verify_report as verify_module
from src.tools.verify_report import verify_report

TRANSCRIPT = "je suis en série D, peut-être médecin, je préfère rester à Cotonou"
GRADES = [{"matiere": "SVT", "note": 15, "lisible": True},
          {"matiere": "Mathématiques", "note": 12, "lisible": True},
          {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12, "lisible": True}]
CALC_INPUTS = [{"matiere": "SVT", "note": 15, "coefficient": 5},
               {"matiere": "Mathématiques", "note": 12, "coefficient": 4},
               {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12, "coefficient": 4}]
CONTEXT = {"serie": "D", "grades": GRADES, "transcript": TRANSCRIPT}


def valid_report():
    return {"schema_version": 1,
            "claims": [
                {"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                 "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                {"claim_id": "doctor-goal", "text": "Tu as dit vouloir être médecin.",
                 "proofs": [{"type": "transcript", "quote": "peut-être médecin"}]},
                {"claim_id": "medecine-bourse", "text": "Médecine Générale : bourses prévues.",
                 "proofs": [{"type": "filiere", "offre_id": "PUB-062", "page_pdf": 36,
                             "champ": "Bourse", "valeur": 95}]},
                {"claim_id": "medecine-calc", "text": "Moyenne de classement pour Médecine.",
                 "proofs": [{"type": "calc", "formula": "M = Σ(mi·ci) / Σci",
                             "inputs": copy.deepcopy(CALC_INPUTS), "result": 13.15}]},
            ]}


def test_correct_report_returns_no_problem():
    assert verify_report(valid_report(), CONTEXT) == []


def test_modified_grade_is_rejected():
    report = valid_report()
    report["claims"][0]["proofs"][0]["note"] = 14
    problems = verify_report(report, CONTEXT)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("svt-grade", "grade")]
    assert problems[0]["reason"]


def test_quote_absent_from_transcript_is_rejected():
    report = valid_report()
    report["claims"][1]["proofs"][0]["quote"] = "je veux être pilote"
    problems = verify_report(report, CONTEXT)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("doctor-goal", "transcript")]


def test_unknown_offre_id_is_rejected():
    report = valid_report()
    report["claims"][2]["proofs"][0]["offre_id"] = "PUB-999"
    problems = verify_report(report, CONTEXT)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("medecine-bourse", "filiere")]


def test_offre_with_status_not_ok_is_rejected():
    report = valid_report()
    # PUB-064 (Pharmacie) exists in the guide but its row is not Statut_qualité = OK.
    report["claims"][2]["proofs"][0] = {"type": "filiere", "offre_id": "PUB-064", "page_pdf": 36,
                                        "champ": "Bourse", "valeur": 18}
    problems = verify_report(report, CONTEXT)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("medecine-bourse", "filiere")]


def test_wrong_filiere_page_or_value_is_rejected():
    for field, wrong in (("page_pdf", 37), ("valeur", 96)):
        report = valid_report()
        report["claims"][2]["proofs"][0][field] = wrong
        problems = verify_report(report, CONTEXT)
        assert [(p["claim_id"], p["type"]) for p in problems] == [("medecine-bourse", "filiere")]


def test_wrong_calc_result_is_rejected_without_leaking_expected_value():
    report = valid_report()
    report["claims"][3]["proofs"][0]["result"] = 14.0
    problems = verify_report(report, CONTEXT)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("medecine-calc", "calc")]
    assert "13.15" not in str(problems)
    assert "13,15" not in str(problems)


def test_calc_with_falsified_coefficient_is_rejected():
    report = valid_report()
    report["claims"][3]["proofs"][0]["inputs"][0]["coefficient"] = 1
    report["claims"][3]["proofs"][0]["result"] = 12.5
    problems = verify_report(report, CONTEXT)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("medecine-calc", "calc")]


def test_claim_without_any_proof_is_a_problem():
    report = valid_report()
    report["claims"][0]["proofs"] = []
    problems = verify_report(report, CONTEXT)
    assert problems
    assert problems[0]["claim_id"] == "svt-grade"


@pytest.mark.parametrize("report", [None, {}, {"schema_version": 1},
                                    {"schema_version": 1, "claims": []},
                                    {"schema_version": 1, "claims": "claims"}])
def test_malformed_report_is_blocked_never_an_empty_list(report):
    problems = verify_report(report, CONTEXT)
    assert problems
    assert all(set(p) == {"claim_id", "type", "reason"} for p in problems)


def test_check_exception_blocks_the_report(monkeypatch):
    def failing_compute(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(verify_module, "compute_ranking_average", failing_compute)
    problems = verify_report(valid_report(), CONTEXT)
    assert [(p["claim_id"], p["type"]) for p in problems] == [("medecine-calc", "calc")]


def test_malformed_context_is_blocked_never_an_empty_list():
    assert verify_report(valid_report(), None)
    assert verify_report(valid_report(), {"serie": "D", "grades": 42, "transcript": TRANSCRIPT})
