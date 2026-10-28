from src.clients.meta_client import get_client
from src.clients.muse_spark import decode_json_answer
from src.clients.profile import request_profile
from src.domain.coefficients import SUPPORTED_SERIES
from src.domain.grade_scale import is_on_grade_scale

# The model may copy a quote with a typographic apostrophe where the transcript
# has a straight one; matching ignores that difference, but the returned quote
# is always cut from the transcript itself.
_APOSTROPHE_TRANSLATION = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'"})


class ProfileError(ValueError):
    """The model answer is not the expected JSON; the caller asks the student instead of guessing."""


def extract_profile(transcript: str, client=None) -> dict:
    """Extract the declared profile from a voice-note transcript.

    `transcript` is the `text` returned by `transcribe_voice`. The result is
    {"serie_declaree", "moyenne_declaree", "interets", "metier_vise",
    "contraintes", "flags"}; every kept field is {"value", "quote"} with
    `quote` copied word for word from the transcript. Validation is code, not
    the model: a field whose quote is missing or not an exact substring is
    rejected here (a scalar becomes None, a list item is dropped), and a field
    the student did not state is None (an empty list for
    `interets`/`contraintes`), never a default. Declared values are kept as
    stated; an unsupported serie or an average outside 0-20 is only flagged in
    `flags` (as `read_grade_sheet` does), never corrected. Declared facts only
    cross-check the grade sheet, they never replace it, and nothing here
    filters offers (docs/prd.md section 2.1), so a stated city stays a
    recorded constraint.
    """
    if not isinstance(transcript, str) or not transcript.strip():
        raise ProfileError("empty transcript: nothing to extract, asking the student instead")
    raw, finish_reason = request_profile(client or get_client(), transcript)
    data = _parse_profile(raw, finish_reason)
    profile = {
        "serie_declaree": _cited_field(data, "serie_declaree", transcript, _serie_value),
        "moyenne_declaree": _cited_field(data, "moyenne_declaree", transcript, _average_value),
        "interets": _cited_list(data, "interets", transcript),
        "metier_vise": _cited_field(data, "metier_vise", transcript, _text_value),
        "contraintes": _cited_list(data, "contraintes", transcript),
    }
    profile["flags"] = _profile_flags(profile)
    return profile


def _parse_profile(raw: str, finish_reason: str) -> dict:
    data = decode_json_answer(raw, finish_reason, ProfileError)
    if not isinstance(data, dict):
        raise ProfileError("schema: the profile must be a JSON object")
    return data


def _cited_field(data: dict, label: str, transcript: str, read_value) -> dict | None:
    return _cited_item(data.get(label), label, transcript, read_value)


def _cited_list(data: dict, label: str, transcript: str) -> list[dict]:
    entry = data.get(label)
    if entry is None:
        return []
    if not isinstance(entry, list):
        raise ProfileError(f"schema: '{label}' must be a list")
    kept = []
    for item in entry:
        checked = _cited_item(item, label, transcript, _text_value)
        if checked is not None:
            kept.append(checked)
    return kept


def _cited_item(entry: object, label: str, transcript: str, read_value) -> dict | None:
    if entry is None:
        return None
    if not isinstance(entry, dict):
        raise ProfileError(f"schema: '{label}' must be an object with 'value' and 'quote' or null")
    value = read_value(entry.get("value"), label)
    if value is None:
        return None
    quote = _verbatim_quote(entry, label, transcript)
    if quote is None:
        return None
    return {"value": value, "quote": quote}


def _verbatim_quote(entry: dict, label: str, transcript: str) -> str | None:
    quote = entry.get("quote")
    if quote is None:
        return None
    if not isinstance(quote, str):
        raise ProfileError(f"schema: 'quote' of '{label}' must be a text")
    if not quote.strip():
        return None
    return _match_quote(quote, transcript)


def _match_quote(quote: str, transcript: str) -> str | None:
    if quote in transcript:
        return quote
    start = transcript.translate(_APOSTROPHE_TRANSLATION).find(
        quote.translate(_APOSTROPHE_TRANSLATION))
    if start < 0:
        return None
    return transcript[start:start + len(quote)]


def _profile_flags(profile: dict) -> list[str]:
    flags = []
    serie = profile["serie_declaree"]
    if serie is not None and serie["value"] not in SUPPORTED_SERIES:
        flags.append("serie_non_prise_en_charge")
    average = profile["moyenne_declaree"]
    if average is not None and not is_on_grade_scale(average["value"]):
        flags.append("moyenne_declaree_hors_plage")
    return flags


def _text_value(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"schema: 'value' of '{label}' must be a non-empty text or null")
    return value.strip()


def _serie_value(value: object, label: str) -> str | None:
    text = _text_value(value, label)
    return text.upper() if text is not None else None


def _average_value(value: object, label: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProfileError(f"schema: 'value' of '{label}' must be a number or null")
    return value
