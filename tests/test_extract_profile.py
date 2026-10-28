import json
from types import SimpleNamespace

import pytest

from src.clients.profile import PROFILE_MAX_TOKENS
from src.tools.extract_profile import ProfileError, extract_profile


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


# The demo sentence of docs/prd.md section 2.1, declared average 14 (contradicts the sheet).
TRANSCRIPT = (
    "Bonjour, je suis en série D, j'ai eu 14 de moyenne. "
    "J'aime beaucoup la biologie et j'aimerais travailler dans la santé, peut-être médecin. "
    "Je préfère rester à Cotonou, et j'aurai besoin d'une bourse."
)


def profile_json(**overrides):
    profile = {
        "serie_declaree": {"value": "D", "quote": "je suis en série D"},
        "moyenne_declaree": {"value": 14, "quote": "j'ai eu 14 de moyenne"},
        "interets": [
            {"value": "biologie", "quote": "J'aime beaucoup la biologie"},
            {"value": "travailler dans la santé", "quote": "j'aimerais travailler dans la santé"},
        ],
        "metier_vise": {"value": "médecin", "quote": "peut-être médecin"},
        "contraintes": [
            {"value": "Cotonou", "quote": "rester à Cotonou"},
            {"value": "bourse", "quote": "besoin d'une bourse"},
        ],
    }
    profile.update(overrides)
    return json.dumps(profile, ensure_ascii=False)


def extract(content, transcript=TRANSCRIPT):
    return extract_profile(transcript, client=FakeClient(content))


def all_quotes(profile):
    quotes = [profile[key]["quote"] for key in ("serie_declaree", "moyenne_declaree", "metier_vise")
              if profile[key] is not None]
    for key in ("interets", "contraintes"):
        quotes.extend(item["quote"] for item in profile[key])
    return quotes


def test_full_profile_is_extracted_with_values():
    profile = extract(profile_json())
    assert profile["serie_declaree"] == {"value": "D", "quote": "je suis en série D"}
    assert profile["moyenne_declaree"] == {"value": 14, "quote": "j'ai eu 14 de moyenne"}
    assert [item["value"] for item in profile["interets"]] == ["biologie", "travailler dans la santé"]
    assert profile["metier_vise"]["value"] == "médecin"
    assert [item["value"] for item in profile["contraintes"]] == ["Cotonou", "bourse"]
    assert profile["flags"] == []


def test_every_quote_is_an_exact_substring_of_the_transcript():
    profile = extract(profile_json())
    assert all_quotes(profile)
    for quote in all_quotes(profile):
        assert quote in TRANSCRIPT


def test_serie_letter_is_uppercased():
    profile = extract(profile_json(serie_declaree={"value": "d", "quote": "je suis en série D"}))
    assert profile["serie_declaree"]["value"] == "D"


def test_invented_quote_nulls_the_scalar_field():
    profile = extract(profile_json(metier_vise={"value": "astronaute", "quote": "je veux être astronaute"}))
    assert profile["metier_vise"] is None
    assert profile["serie_declaree"]["value"] == "D"


def test_invented_quote_drops_the_list_item():
    profile = extract(profile_json(interets=[
        {"value": "biologie", "quote": "J'aime beaucoup la biologie"},
        {"value": "espace", "quote": "j'adore l'astronomie"},
    ]))
    assert [item["value"] for item in profile["interets"]] == ["biologie"]


def test_field_without_quote_is_rejected():
    profile = extract(profile_json(serie_declaree={"value": "D"}))
    assert profile["serie_declaree"] is None


def test_empty_quote_is_not_a_citation():
    profile = extract(profile_json(metier_vise={"value": "médecin", "quote": ""}))
    assert profile["metier_vise"] is None


def test_quote_is_checked_for_existence_not_meaning():
    # Only existence is code's job (as for transcript proofs); matching the
    # quote to the value is the model's, so a verbatim quote is kept as is.
    profile = extract(profile_json(contraintes=[{"value": "bourse", "quote": "je suis en série D"}]))
    assert profile["contraintes"] == [{"value": "bourse", "quote": "je suis en série D"}]


def test_undisclosed_fields_are_null_and_lists_empty():
    empty = {"serie_declaree": None, "moyenne_declaree": None,
             "interets": [], "metier_vise": None, "contraintes": [], "flags": []}
    model_answer = {key: value for key, value in empty.items() if key != "flags"}
    assert extract(json.dumps(model_answer, ensure_ascii=False)) == empty


def test_missing_keys_are_treated_as_undisclosed():
    profile = extract(json.dumps({"serie_declaree": {"value": "D", "quote": "je suis en série D"}},
                                 ensure_ascii=False))
    assert profile["moyenne_declaree"] is None
    assert profile["interets"] == []
    assert profile["contraintes"] == []


def test_cotonou_is_recorded_as_a_constraint():
    profile = extract(profile_json())
    assert "Cotonou" in [item["value"] for item in profile["contraintes"]]


def test_invalid_json_raises_typed_error():
    with pytest.raises(ProfileError, match="JSON"):
        extract("pas du json")


def test_non_object_answer_raises_typed_error():
    with pytest.raises(ProfileError, match="object"):
        extract('["D", 14]')


def test_empty_answer_with_length_signals_token_limit():
    with pytest.raises(ProfileError, match="max_tokens"):
        extract_profile(TRANSCRIPT, client=FakeClient("", finish_reason="length"))


def test_truncated_json_with_length_signals_token_limit():
    with pytest.raises(ProfileError, match="max_tokens"):
        extract_profile(TRANSCRIPT, client=FakeClient('{"serie_declaree": {"val',
                                                      finish_reason="length"))


def test_non_numeric_declared_average_raises_typed_error():
    with pytest.raises(ProfileError, match="moyenne_declaree"):
        extract(profile_json(moyenne_declaree={"value": "quatorze", "quote": "j'ai eu 14 de moyenne"}))


def test_non_text_list_value_raises_typed_error():
    with pytest.raises(ProfileError, match="interets"):
        extract(profile_json(interets=[{"value": 42, "quote": "j'ai eu 14 de moyenne"}]))


def test_non_list_interets_raises_typed_error():
    with pytest.raises(ProfileError, match="interets"):
        extract(profile_json(interets={"value": "biologie", "quote": "J'aime beaucoup la biologie"}))


def test_empty_transcript_raises_typed_error():
    with pytest.raises(ProfileError, match="transcript"):
        extract_profile("   ", client=FakeClient(profile_json()))


def test_transcript_is_sent_with_wide_token_limit():
    client = FakeClient(profile_json())
    extract_profile(TRANSCRIPT, client=client)
    call = client.calls[0]
    assert call["max_tokens"] == PROFILE_MAX_TOKENS
    assert TRANSCRIPT in json.dumps(call["messages"], ensure_ascii=False)


# Real `text` returned by transcribe_voice on the coherent note (2026-10-28,
# issue #16): numbers in words, hesitations, repeated words, no punctuation
# runs. Quotes below are cut from it unchanged.
REAL_TRANSCRIPT = (
    "Bonjour, alors euh je suis en terminale série D D comme Daniel au bac "
    "j'ai eu onze virgule deux de moyenne ce que j'aime le plus c'est la biologie "
    "les SVT vraiment c'est ma matière préférée plus tard j'aimerais travailler "
    "dans la santé peut-être médecin depuis petite je veux soigner les gens "
    "aider ma famille mon quartier pour la ville euh Je préfère rester à Cotonou, "
    "près de mes parents, parents et honnêtement, j'aurais besoin d'une bourse "
    "parce que les études euh ça coûte cher chez nous. Voilà. Merci de m'écouter"
)


def test_real_transcript_with_numbers_in_words():
    content = json.dumps({
        "serie_declaree": {"value": "D", "quote": "série D"},
        "moyenne_declaree": {"value": 11.2, "quote": "onze virgule deux de moyenne"},
        "interets": [
            {"value": "la biologie", "quote": "la biologie"},
            {"value": "les SVT", "quote": "les SVT"},
        ],
        "metier_vise": {"value": "médecin", "quote": "peut-être médecin"},
        "contraintes": [
            {"value": "Cotonou", "quote": "Je préfère rester à Cotonou, près de mes parents, parents"},
            {"value": "bourse", "quote": "j'aurais besoin d'une bourse"},
        ],
    }, ensure_ascii=False)
    profile = extract(content, transcript=REAL_TRANSCRIPT)
    assert profile["serie_declaree"]["value"] == "D"
    assert profile["moyenne_declaree"]["value"] == 11.2
    assert profile["metier_vise"]["value"] == "médecin"
    assert [item["value"] for item in profile["contraintes"]] == ["Cotonou", "bourse"]
    for quote in all_quotes(profile):
        assert quote in REAL_TRANSCRIPT


def test_typographic_apostrophe_quote_is_matched_back_to_the_transcript():
    profile = extract(profile_json(interets=[
        {"value": "travailler dans la santé", "quote": "j’aimerais travailler dans la santé"},
    ]))
    assert profile["interets"] == [
        {"value": "travailler dans la santé", "quote": "j'aimerais travailler dans la santé"}]
    assert profile["interets"][0]["quote"] in TRANSCRIPT


def test_out_of_range_declared_average_is_kept_and_flagged():
    profile = extract(profile_json(
        moyenne_declaree={"value": 25, "quote": "j'ai eu 14 de moyenne"}))
    assert profile["moyenne_declaree"]["value"] == 25
    assert profile["flags"] == ["moyenne_declaree_hors_plage"]


def test_unsupported_declared_serie_is_kept_and_flagged():
    transcript = "Bonjour, je suis en série Z, j'ai eu 12 de moyenne."
    content = json.dumps({
        "serie_declaree": {"value": "Z", "quote": "je suis en série Z"},
        "moyenne_declaree": {"value": 12, "quote": "j'ai eu 12 de moyenne"},
    }, ensure_ascii=False)
    profile = extract(content, transcript=transcript)
    assert profile["serie_declaree"]["value"] == "Z"
    assert profile["flags"] == ["serie_non_prise_en_charge"]
