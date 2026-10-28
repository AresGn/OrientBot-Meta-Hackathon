import pytest

from src.clients.muse_spark import (
    MUSE_SPARK_MAX_TOKENS,
    MUSE_SPARK_MODEL,
    decode_json_answer,
    request_answer,
)
from tests.fake_client import FakeClient


class AnswerError(ValueError):
    pass


def test_request_sends_one_user_message_with_the_model_parameters():
    client = FakeClient('{"ok": true}')
    content = [{"type": "text", "text": "consigne"}]
    request_answer(client, content)
    call = client.calls[0]
    assert call["model"] == MUSE_SPARK_MODEL
    assert call["max_tokens"] == MUSE_SPARK_MAX_TOKENS
    assert call["messages"] == [{"role": "user", "content": content}]


def test_request_returns_raw_text_and_finish_reason():
    assert request_answer(FakeClient('{"ok": true}', finish_reason="stop"), []) == ('{"ok": true}', "stop")


def test_missing_content_becomes_empty_text():
    assert request_answer(FakeClient(None, finish_reason="length"), []) == ("", "length")


def test_valid_json_is_decoded():
    assert decode_json_answer('{"serie": "D"}', "stop", AnswerError) == {"serie": "D"}


def test_empty_answer_with_length_signals_token_limit():
    with pytest.raises(AnswerError, match="empty answer.*max_tokens"):
        decode_json_answer("", "length", AnswerError)


def test_truncated_answer_with_length_signals_token_limit():
    with pytest.raises(AnswerError, match="cut off.*max_tokens"):
        decode_json_answer('{"serie": "D", "mat', "length", AnswerError)


def test_invalid_json_raises_the_caller_error_type():
    with pytest.raises(AnswerError, match="not valid JSON"):
        decode_json_answer("pas du json", "stop", AnswerError)
