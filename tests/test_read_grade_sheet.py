import json
from types import SimpleNamespace

import pytest

from src.tools.read_grade_sheet import GradeSheetError, read_grade_sheet


class FakeClient:
    """Mimics client.chat.completions.create; never touches the network."""

    def __init__(self, content, finish_reason="stop"):
        choice = SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._response = SimpleNamespace(choices=[choice])

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def sheet_json(rows, serie="D"):
    return json.dumps({"serie": serie, "matieres": rows, "moyenne_affichee": 11.2})


def row(matiere, note, lisible=True):
    return {"matiere": matiere, "note": note, "coeff": 2, "lisible": lisible}


@pytest.fixture
def image(tmp_path):
    path = tmp_path / "sheet.jpg"
    path.write_bytes(b"\xff\xd8fake")
    return str(path)


def read(image, rows, serie="D"):
    return read_grade_sheet(image, client=FakeClient(sheet_json(rows, serie)))


def by_subject(result):
    return {r["matiere"]: r for r in result["matieres"]}


def test_valid_sheet_is_normalized_and_unflagged(image):
    result = read(image, [row("MATHEMATIQUES", 12), row("SCIENCES DE LA VIE ET DE LA TERRE", 15),
                          row("FRANCAIS", 9.5)])
    assert result["serie"] == "D"
    assert by_subject(result)["Mathématiques"] == {"matiere": "Mathématiques", "note": 12, "lisible": True, "flags": []}
    assert by_subject(result)["SVT"]["note"] == 15
    assert by_subject(result)["Français"]["note"] == 9.5


def test_unreadable_grade_is_null_and_not_readable(image):
    entry = by_subject(read(image, [row("MATHEMATIQUES", None, lisible=False)]))["Mathématiques"]
    assert entry["note"] is None
    assert entry["lisible"] is False


def test_note_given_with_unreadable_flag_is_dropped(image):
    entry = by_subject(read(image, [row("MATHEMATIQUES", 12, lisible=False)]))["Mathématiques"]
    assert entry["note"] is None


def test_readable_without_note_is_marked_unreadable(image):
    entry = by_subject(read(image, [row("MATHEMATIQUES", None, lisible=True)]))["Mathématiques"]
    assert entry["lisible"] is False and entry["note"] is None


@pytest.mark.parametrize("note", [21, -1, 25.5])
def test_out_of_range_note_is_flagged_not_corrected(image, note):
    entry = by_subject(read(image, [row("MATHEMATIQUES", note)]))["Mathématiques"]
    assert entry["note"] == note
    assert "note_hors_plage" in entry["flags"]


def test_unknown_subject_is_flagged_and_kept_as_printed(image):
    entry = by_subject(read(image, [row("ASTROLOGIE", 14)]))["ASTROLOGIE"]
    assert "matiere_inconnue" in entry["flags"]
    assert entry["note"] == 14


def test_eps_is_not_flagged(image):
    entry = by_subject(read(image, [row("EDUCATION PHYSIQUE ET SPORTIVE", 10.5)]))["EPS"]
    assert entry["flags"] == []


def test_invalid_json_raises_typed_error(image):
    with pytest.raises(GradeSheetError, match="JSON"):
        read_grade_sheet(image, client=FakeClient("pas du json"))


def test_schema_violation_raises_typed_error(image):
    with pytest.raises(GradeSheetError, match="matieres"):
        read_grade_sheet(image, client=FakeClient('{"serie": "D"}'))


def test_non_numeric_note_raises_typed_error(image):
    with pytest.raises(GradeSheetError, match="note"):
        read(image, [row("MATHEMATIQUES", "douze")])


def test_empty_content_with_length_signals_token_limit(image):
    with pytest.raises(GradeSheetError, match="max_tokens"):
        read_grade_sheet(image, client=FakeClient("", finish_reason="length"))


def test_unsupported_serie_is_flagged_on_every_row(image):
    result = read(image, [row("MATHEMATIQUES", 12)], serie="A1")
    assert "serie_non_prise_en_charge" in by_subject(result)["Mathématiques"]["flags"]


def test_image_is_sent_as_data_url_with_wide_token_limit(image):
    client = FakeClient(sheet_json([row("MATHEMATIQUES", 12)]))
    read_grade_sheet(image, client=client)
    call = client.calls[0]
    assert call["max_tokens"] >= 8000
    assert call["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_missing_image_raises_typed_error():
    with pytest.raises(GradeSheetError, match="image"):
        read_grade_sheet("nope.jpg", client=FakeClient("{}"))
