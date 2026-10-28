import math

import pytest

from src.domain.proofs import SCHEMA_VERSION, validate_proof, validate_report

CALC_INPUTS = [{"matiere": "SVT", "note": 15, "coefficient": 5},
               {"matiere": "Mathématiques", "note": 12, "coefficient": 4},
               {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12, "coefficient": 4}]


def test_grade_proof_with_matiere_and_note_is_valid():
    assert validate_proof({"type": "grade", "matiere": "SVT", "note": 15}) == []


def test_transcript_proof_with_quote_is_valid():
    assert validate_proof({"type": "transcript", "quote": "peut-être médecin"}) == []


def test_filiere_proof_with_champ_and_valeur_is_valid():
    proof = {"type": "filiere", "offre_id": "PUB-062", "page_pdf": 36, "champ": "Bourse", "valeur": 95}
    assert validate_proof(proof) == []


def test_calc_proof_with_typed_inputs_is_valid():
    proof = {"type": "calc", "formula": "M = Σ(mi·ci) / Σci", "inputs": CALC_INPUTS, "result": 13.15}
    assert validate_proof(proof) == []


def test_report_with_ids_and_proofs_is_valid():
    report = {"schema_version": SCHEMA_VERSION,
              "claims": [{"claim_id": "svt-grade", "text": "SVT : 15/20 au relevé.",
                          "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                         {"claim_id": "doctor-goal", "text": "Tu as dit vouloir être médecin.",
                          "proofs": [{"type": "transcript", "quote": "peut-être médecin"}]},
                         {"claim_id": "medecine-access",
                          "text": "Médecine Générale : 95 bourses prévues, moyenne 13,15.",
                          "proofs": [{"type": "filiere", "offre_id": "PUB-062", "page_pdf": 36,
                                      "champ": "Bourse", "valeur": 95},
                                     {"type": "calc", "formula": "M = Σ(mi·ci) / Σci",
                                      "inputs": CALC_INPUTS, "result": 13.15}]}]}
    assert validate_report(report) == []


def test_proof_with_missing_field_is_invalid():
    assert validate_proof({"type": "grade", "matiere": "SVT"}) == ["grade: missing field 'note'"]


def test_proof_with_wrong_field_type_is_invalid():
    proof = {"type": "filiere", "offre_id": "PUB-062", "page_pdf": "36", "champ": "Bourse", "valeur": 95}
    assert validate_proof(proof) == ["filiere: 'page_pdf' must be a positive integer"]


def test_proof_with_unknown_type_is_invalid():
    assert validate_proof({"type": "vibes", "quote": "peut-être médecin"}) == ["unknown proof type: 'vibes'"]


def test_proof_with_unknown_field_is_invalid():
    assert validate_proof({"type": "grade", "matiere": "SVT", "note": 15, "coeff": 5}) == [
        "grade: unknown field 'coeff'"]


def test_claim_without_proof_is_invalid():
    report = {"schema_version": SCHEMA_VERSION,
              "claims": [{"claim_id": "admission", "text": "Tu seras admis.", "proofs": []}]}
    assert validate_report(report) == [
        {"claim_id": "admission", "type": "structure", "reason": "carries no proof"}]


def test_claim_without_id_is_invalid():
    report = {"schema_version": SCHEMA_VERSION,
              "claims": [{"text": "SVT : 15/20.",
                          "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]}]}
    assert validate_report(report) == [
        {"claim_id": None, "type": "structure", "reason": "missing claim_id"}]


def test_duplicate_claim_id_is_invalid():
    claim = {"claim_id": "svt-grade", "text": "SVT : 15/20.",
             "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]}
    report = {"schema_version": SCHEMA_VERSION, "claims": [claim, dict(claim)]}
    assert validate_report(report) == [
        {"claim_id": "svt-grade", "type": "structure", "reason": "duplicate claim_id"}]


def test_report_with_wrong_schema_version_is_invalid():
    report = {"schema_version": 99, "claims": [{"claim_id": "svt-grade", "text": "SVT : 15/20.",
              "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]}]}
    assert validate_report(report) == [
        {"claim_id": None, "type": "structure", "reason": "unsupported schema_version: 99 (want 1)"}]


def test_non_object_proof_and_report_are_invalid():
    assert validate_proof("SVT 15") == ["proof must be an object"]
    assert validate_report([]) == [
        {"claim_id": None, "type": "structure", "reason": "report must be an object"}]


@pytest.mark.parametrize("report", [None, {}, {"schema_version": SCHEMA_VERSION},
                                    {"schema_version": SCHEMA_VERSION, "claims": []}])
def test_malformed_report_is_blocked_never_empty(report):
    assert validate_report(report) != []


def test_filiere_proof_without_champ_is_invalid():
    proof = {"type": "filiere", "offre_id": "PUB-062", "page_pdf": 36, "valeur": 95}
    assert validate_proof(proof) == ["filiere: missing field 'champ'"]


@pytest.mark.parametrize("valeur", [True, "", ["95"], math.nan])
def test_filiere_valeur_must_be_a_string_or_a_finite_number(valeur):
    proof = {"type": "filiere", "offre_id": "PUB-062", "page_pdf": 36, "champ": "Bourse", "valeur": valeur}
    assert validate_proof(proof) == ["filiere: 'valeur' must be a non-empty string or a finite number"]


@pytest.mark.parametrize(("entry", "reason"), [
    ({"matiere": "SVT", "note": 15}, "calc: inputs[0]: missing field 'coefficient'"),
    ({"matiere": "SVT", "note": "15", "coefficient": 5},
     "calc: inputs[0]: 'note' must be a finite number"),
    ({"matiere": "SVT", "note": 15, "coefficient": 0},
     "calc: inputs[0]: 'coefficient' must be a positive integer"),
    ("SVT 15", "calc: inputs[0] must be an object"),
])
def test_calc_inputs_entry_is_typed(entry, reason):
    proof = {"type": "calc", "formula": "M = Σ(mi·ci) / Σci", "inputs": [entry], "result": 13.15}
    assert validate_proof(proof) == [reason]


@pytest.mark.parametrize(("proof", "reason"), [
    ({"type": "grade", "matiere": "SVT", "note": math.nan}, "grade: 'note' must be a finite number"),
    ({"type": "grade", "matiere": "SVT", "note": math.inf}, "grade: 'note' must be a finite number"),
    ({"type": "calc", "formula": "M = Σ(mi·ci) / Σci", "inputs": CALC_INPUTS, "result": math.inf},
     "calc: 'result' must be a finite number"),
])
def test_non_finite_number_is_invalid(proof, reason):
    assert validate_proof(proof) == [reason]
