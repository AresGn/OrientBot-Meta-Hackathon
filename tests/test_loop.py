import json
from types import SimpleNamespace

import pytest

from src.agent import loop
from tests.fake_client import ScriptedFakeClient

QUESTION = "Quelle est ta note en SVT ?"
ANSWER = "Ma note en SVT est 15 sur 20."


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)),
    )


def assistant_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def asking_client(*extra_messages):
    ask = assistant_message(tool_calls=[tool_call("call-ask", "ask_student", {"question": QUESTION})])
    return ScriptedFakeClient([ask, *extra_messages])


def tool_observations(call_snapshot):
    return [message for message in call_snapshot["messages"]
            if isinstance(message, dict) and message.get("role") == "tool"]


def test_loop_returns_needs_input_when_model_asks_student():
    client = asking_client()
    result = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    assert result["status"] == "needs_input"
    assert result["question"] == QUESTION
    assert len(client.calls) == 1


def test_without_answer_no_further_model_or_tool_call_is_made(monkeypatch):
    executed = []
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: executed.append(kwargs))
    ask = assistant_message(tool_calls=[
        tool_call("call-ask", "ask_student", {"question": QUESTION}),
        tool_call("call-lookup", "lookup_filieres", {"serie": "D"}),
    ])
    client = ScriptedFakeClient([ask])
    result = loop.run(client, "fake-model", [], "Je veux être médecin.")
    assert result["status"] == "needs_input"
    assert len(client.calls) == 1
    assert executed == []


def test_resume_answers_every_pending_tool_call(monkeypatch):
    # Regression: the real API refuses a resumed history where a tool call
    # from the same assistant message (here lookup_filieres, asked alongside
    # ask_student) never got a tool response. ScriptedFakeClient raises in
    # that case, so reaching the final text proves every call was answered.
    executed = []
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: executed.append(kwargs))
    ask = assistant_message(tool_calls=[
        tool_call("call-ask", "ask_student", {"question": QUESTION}),
        tool_call("call-lookup", "lookup_filieres", {"serie": "D"}),
    ])
    client = ScriptedFakeClient([ask, assistant_message(content="Merci, je continue.")])
    suspended = loop.run(client, "fake-model", [], "Je veux être médecin.")
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result == "Merci, je continue."
    assert executed == []  # answered with an error, never executed
    observations = tool_observations(client.calls[1])
    by_id = {message["tool_call_id"]: message["content"] for message in observations}
    assert ANSWER in by_id["call-ask"]
    assert "not executed" in by_id["call-lookup"]


def test_only_the_first_question_is_surfaced_when_model_asks_two():
    ask = assistant_message(tool_calls=[
        tool_call("call-ask-1", "ask_student", {"question": QUESTION}),
        tool_call("call-ask-2", "ask_student", {"question": "Quelle est ta série ?"}),
    ])
    client = ScriptedFakeClient([ask, assistant_message(content="Merci, je continue.")])
    suspended = loop.run(client, "fake-model", [], "Bonjour.")
    assert suspended["question"] == QUESTION
    assert len(client.calls) == 1
    # The second question was never executed: on resume it gets the
    # "not executed" error, so the strict fake client accepts the history.
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result == "Merci, je continue."
    by_id = {m["tool_call_id"]: m["content"] for m in tool_observations(client.calls[1])}
    assert ANSWER in by_id["call-ask-1"]
    assert "not executed" in by_id["call-ask-2"]


def test_resume_feeds_the_answer_as_a_tool_observation():
    client = asking_client(assistant_message(content="Merci, je continue."))
    suspended = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result == "Merci, je continue."
    assert len(client.calls) == 2
    observations = tool_observations(client.calls[1])
    assert observations
    assert observations[-1]["tool_call_id"] == "call-ask"
    assert ANSWER in observations[-1]["content"]


def test_resume_without_an_answer_makes_no_model_call():
    client = asking_client(assistant_message(content="Merci, je continue."))
    suspended = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    result = loop.resume(client, "fake-model", [], suspended, "   ")
    assert result["status"] == "needs_input"
    assert result["question"] == QUESTION
    assert len(client.calls) == 1


def test_resume_with_a_malformed_state_fails_loudly():
    client = asking_client()
    with pytest.raises(KeyError):
        loop.resume(client, "fake-model", [], {"status": "needs_input"}, ANSWER)
    assert client.calls == []


def test_repeated_questions_stop_at_the_twelfth_step():
    scripted = [assistant_message(tool_calls=[
        tool_call(f"call-ask-{step}", "ask_student", {"question": QUESTION})])
        for step in range(loop.MAX_STEPS)]
    client = ScriptedFakeClient(scripted)
    result = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    while isinstance(result, dict) and result.get("status") == "needs_input":
        result = loop.resume(client, "fake-model", [], result, ANSWER)
    assert result == "Stopped: step limit reached."
    assert len(client.calls) == loop.MAX_STEPS


def test_empty_question_from_the_model_is_an_observation_not_a_suspension():
    empty_ask = assistant_message(tool_calls=[tool_call("call-ask", "ask_student", {"question": "  "})])
    client = ScriptedFakeClient([empty_ask, assistant_message(content="Je reformule.")])
    result = loop.run(client, "fake-model", [], "Bonjour.")
    assert result == "Je reformule."
    assert len(client.calls) == 2
    observations = tool_observations(client.calls[1])
    assert observations and "non-empty" in observations[-1]["content"]
