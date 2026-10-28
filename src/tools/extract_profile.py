import json

from src.clients.meta_client import get_client
from src.clients.profile import request_profile


class ProfileError(ValueError):
    """The model answer is not the expected JSON; the caller asks the student instead of guessing."""


def extract_profile(transcript: str, client=None) -> dict:
    """Extract the declared profile from a voice-note transcript.

    `transcript` is the `text` returned by `transcribe_voice`. The result is
    {"serie_declaree", "moyenne_declaree", "interets", "metier_vise",
    "contraintes"}; every kept field is {"value", "quote"} with `quote` copied
    word for word from the transcript. Validation is code, not the model: a
    field whose quote is missing or not an exact substring is rejected here
    (a scalar becomes None, a list item is dropped), and a field the student
    did not state is None (an empty list for `interets`/`contraintes`), never
    a default. Declared facts only cross-check the grade sheet, they never
    replace it, and nothing here filters offers (docs/prd.md section 2.1), so
    a stated city stays a recorded constraint.
    """
    if not isinstance(transcript, str) or not transcript.strip():
        raise ProfileError("empty transcript: nothing to extract, asking the student instead")
    raw, finish_reason = request_profile(client or get_client(), transcript)
    data = _parse_profile(raw, finish_reason)
    return {
        "serie_declaree": _field(data.get("serie_declaree"), transcript, "serie_declaree", _serie_value),
        "moyenne_declaree": _field(data.get("moyenne_declaree"), transcript, "moyenne_declaree", _average_value),
        "interets": _list_field(data.get("interets"), transcript, "interets"),
        "metier_vise": _field(data.get("metier_vise"), transcript, "metier_vise", _text_value),
        "contraintes": _list_field(data.get("contraintes"), transcript, "contraintes"),
    }


def _parse_profile(raw: str, finish_reason: str) -> dict:
    if not raw.strip() and finish_reason == "length":
        raise ProfileError("empty answer, finish_reason=length: max_tokens too low")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        if finish_reason == "length":
            raise ProfileError("answer cut off, finish_reason=length: max_tokens too low") from error
        raise ProfileError(f"model answer is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ProfileError("schema: the profile must be a JSON object")
    return data


def _field(entry: object, transcript: str, label: str, read_value) -> dict | None:
    if entry is None:
        return None
    if not isinstance(entry, dict):
        raise ProfileError(f"schema: '{label}' must be an object with 'value' and 'quote' or null")
    value = read_value(entry.get("value"), label)
    if value is None:
        return None
    quote = _quote(entry, label)
    if quote is None or quote not in transcript:
        return None
    return {"value": value, "quote": quote}


def _list_field(entry: object, transcript: str, label: str) -> list[dict]:
    if entry is None:
        return []
    if not isinstance(entry, list):
        raise ProfileError(f"schema: '{label}' must be a list")
    kept = []
    for item in entry:
        checked = _field(item, transcript, label, _text_value)
        if checked is not None:
            kept.append(checked)
    return kept


def _quote(entry: dict, label: str) -> str | None:
    quote = entry.get("quote")
    if quote is None:
        return None
    if not isinstance(quote, str):
        raise ProfileError(f"schema: 'quote' of '{label}' must be a text")
    return quote if quote.strip() else None


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
        raise ProfileError("schema: 'value' of 'moyenne_declaree' must be a number or null")
    return value
