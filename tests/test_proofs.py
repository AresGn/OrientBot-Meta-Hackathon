from src.domain.proofs import SCHEMA_VERSION, validate_proof, validate_report


def test_grade_proof_with_matiere_and_note_is_valid():
    assert validate_proof({"type": "grade", "matiere": "SVT", "note": 15}) == []


def test_transcript_proof_with_quote_is_valid():
    assert validate_proof({"type": "transcript", "quote": "peut-être médecin"}) == []


def test_filiere_proof_with_offre_id_and_page_is_valid():
    assert validate_proof({"type": "filiere", "offre_id": "PUB-062", "page_pdf": 36}) == []


def test_calc_proof_with_formula_inputs_and_result_is_valid():
    proof = {"type": "calc", "formula": "M = Σ(mi·ci) / Σci",
             "inputs": [{"matiere": "SVT", "note": 15, "coefficient": 5},
                        {"matiere": "Mathématiques", "note": 12, "coefficient": 4},
                        {"matiere": "Sciences Physiques (PCT/SPCT)", "note": 12, "coefficient": 4}],
             "result": 13.15}
    assert validate_proof(proof) == []


def test_report_where_each_claim_has_a_proof_is_valid():
    report = {"schema_version": SCHEMA_VERSION,
              "claims": [{"text": "SVT : 15/20 au relevé.",
                          "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]},
                         {"text": "Tu as dit vouloir être médecin (« peut-être médecin »).",
                          "proofs": [{"type": "transcript", "quote": "peut-être médecin"}]},
                         {"text": "Médecine Générale (FSS) est accessible en série D, "
                                  "moyenne de classement 13,15.",
                          "proofs": [{"type": "filiere", "offre_id": "PUB-062", "page_pdf": 36},
                                     {"type": "calc", "formula": "M = Σ(mi·ci) / Σci",
                                      "inputs": [{"matiere": "SVT", "note": 15, "coefficient": 5}],
                                      "result": 13.15}]}]}
    assert validate_report(report) == []


def test_proof_with_missing_field_is_invalid():
    assert validate_proof({"type": "grade", "matiere": "SVT"}) == ["grade: missing field 'note'"]


def test_proof_with_wrong_field_type_is_invalid():
    problems = validate_proof({"type": "filiere", "offre_id": "PUB-062", "page_pdf": "36"})
    assert problems == ["filiere: 'page_pdf' must be a positive integer"]


def test_proof_with_unknown_type_is_invalid():
    assert validate_proof({"type": "vibes", "quote": "peut-être médecin"}) == ["unknown proof type: 'vibes'"]


def test_claim_without_proof_is_invalid():
    report = {"schema_version": SCHEMA_VERSION,
              "claims": [{"text": "Tu seras admis.", "proofs": []}]}
    assert validate_report(report) == ["claim 0: carries no proof"]


def test_report_with_wrong_schema_version_is_invalid():
    report = {"schema_version": 99, "claims": [{"text": "SVT : 15/20 au relevé.",
              "proofs": [{"type": "grade", "matiere": "SVT", "note": 15}]}]}
    assert validate_report(report) == ["unsupported schema_version: 99 (want 1)"]


def test_non_object_proof_and_report_are_invalid():
    assert validate_proof("SVT 15") == ["proof must be an object"]
    assert validate_report([]) == ["report must be an object"]
