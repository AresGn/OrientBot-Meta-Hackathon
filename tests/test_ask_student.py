import json
from types import SimpleNamespace

import pytest

from src.agent import loop
from src.tools.ask_student import AskStudentError, ask_student

QUESTION = "Quelle est ta note en SVT ?"
ANSWER = "Ma note en SVT est 15 sur 20."


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)),
    )


def assistant_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


class FakeClient:
    """Scripted model: returns one prepared message per create() call."""

    def __init__(self, scripted_messages):
        self.calls = []
        self._scripted = list(scripted_messages)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        # Snapshot: the loop mutates the same messages list afterwards.
        snapshot = dict(kwargs)
        snapshot["messages"] = list(kwargs["messages"])
        self.calls.append(snapshot)
        message = self._scripted.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def asking_client(*extra_messages):
    ask = assistant_message(tool_calls=[tool_call("call-ask", "ask_student", {"question": QUESTION})])
    return FakeClient([ask, *extra_messages])


def test_ask_student_returns_needs_input_with_the_question():
    assert ask_student(QUESTION) == {"status": "needs_input", "question": QUESTION}


def test_ask_student_strips_surrounding_whitespace():
    assert ask_student(f"  {QUESTION}  ") == {"status": "needs_input", "question": QUESTION}


def test_ask_student_rejects_an_empty_question():
    with pytest.raises(AskStudentError, match="non-empty"):
        ask_student("   ")


def test_ask_student_rejects_two_questions_at_once():
    with pytest.raises(AskStudentError, match="one question"):
        ask_student("Quelle est ta série ? Et ta note en SVT ?")


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
    client = FakeClient([ask])
    result = loop.run(client, "fake-model", [], "Je veux être médecin.")
    assert result["status"] == "needs_input"
    assert len(client.calls) == 1
    assert executed == []


def test_only_the_first_question_is_surfaced_when_model_asks_two():
    ask = assistant_message(tool_calls=[
        tool_call("call-ask-1", "ask_student", {"question": QUESTION}),
        tool_call("call-ask-2", "ask_student", {"question": "Quelle est ta série ?"}),
    ])
    client = FakeClient([ask])
    result = loop.run(client, "fake-model", [], "Bonjour.")
    assert result["question"] == QUESTION
    assert len(client.calls) == 1


def test_resume_feeds_the_answer_as_a_tool_observation():
    client = asking_client(assistant_message(content="Merci, je continue."))
    suspended = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result == "Merci, je continue."
    assert len(client.calls) == 2
    observations = [message for message in client.calls[1]["messages"]
                    if isinstance(message, dict) and message.get("role") == "tool"]
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


def test_empty_question_from_the_model_is_an_observation_not_a_suspension():
    empty_ask = assistant_message(tool_calls=[tool_call("call-ask", "ask_student", {"question": "  "})])
    client = FakeClient([empty_ask, assistant_message(content="Je reformule.")])
    result = loop.run(client, "fake-model", [], "Bonjour.")
    assert result == "Je reformule."
    assert len(client.calls) == 2
    observations = [message for message in client.calls[1]["messages"]
                    if isinstance(message, dict) and message.get("role") == "tool"]
    assert observations and "non-empty" in observations[-1]["content"]
