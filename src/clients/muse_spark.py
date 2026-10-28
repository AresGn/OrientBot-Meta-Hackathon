"""Muse Spark 1.3 chat call shared by the tools; the only place that knows its model parameters."""
import json

MUSE_SPARK_MODEL = "muse-spark-1.3"
MUSE_SPARK_MAX_TOKENS = 8000  # docs/decisions.md E0.4: reasoning tokens count, 8000 suffices (finish_reason = stop)


def request_answer(client, content: list[dict]) -> tuple[str, str]:
    """Send one user message to the model; return (raw answer text, finish_reason)."""
    response = client.chat.completions.create(model=MUSE_SPARK_MODEL,
                                              messages=[{"role": "user", "content": content}],
                                              max_tokens=MUSE_SPARK_MAX_TOKENS)
    choice = response.choices[0]
    return choice.message.content or "", choice.finish_reason


def decode_json_answer(raw: str, finish_reason: str, error_type: type[ValueError]) -> object:
    """Decode the model's JSON answer, raising the caller's `error_type` with the reason.

    Reasoning tokens count in `max_tokens`, so `finish_reason = length` names
    the token limit rather than a bad answer (docs/decisions.md E0.4).
    """
    if not raw.strip() and finish_reason == "length":
        raise error_type("empty answer, finish_reason=length: max_tokens too low")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        if finish_reason == "length":
            raise error_type("answer cut off, finish_reason=length: max_tokens too low") from error
        raise error_type(f"model answer is not valid JSON: {error}") from error
