from types import SimpleNamespace


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


class ScriptedFakeClient:
    """Returns one prepared message per create() call; never touches the network.

    Refuses, like the real API, a history where a tool call has no tool
    response: every `tool_call_id` asked by an assistant message must have a
    matching `role: tool` message before the next model call.
    """

    def __init__(self, scripted_messages):
        self.calls = []
        self._scripted = list(scripted_messages)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        _reject_unanswered_tool_calls(kwargs["messages"])
        # Snapshot: the loop mutates the same messages list afterwards.
        snapshot = dict(kwargs)
        snapshot["messages"] = list(kwargs["messages"])
        self.calls.append(snapshot)
        message = self._scripted.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _reject_unanswered_tool_calls(messages):
    answered = {message.get("tool_call_id") for message in messages
                if isinstance(message, dict) and message.get("role") == "tool"}
    missing = [call.id for message in messages
               for call in (getattr(message, "tool_calls", None) or [])
               if call.id not in answered]
    if missing:
        raise AssertionError(f"tool_call_ids did not have response messages: {missing}")
