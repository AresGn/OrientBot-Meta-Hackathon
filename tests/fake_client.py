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
