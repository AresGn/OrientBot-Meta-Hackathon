import json
import wave
from types import SimpleNamespace

import httpx
import pytest

from src.tools.transcribe_voice import MAX_AUDIO_BYTES, TranscriptionError, transcribe_voice


class FakeResponse:
    """Mimics httpx.Response; never touches the network."""

    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body if body is not None else {"transcript": "bonjour"}

    @property
    def text(self):
        return json.dumps(self._body)

    def json(self):
        return self._body


class FakePost:
    """Stands in for httpx.post and records its calls."""

    def __init__(self, response=None, error=None):
        self.response = response if response is not None else FakeResponse()
        self.error = error
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
        return self.response


@pytest.fixture
def client():
    return SimpleNamespace(base_url="https://test.invalid/v1/", api_key="fake")


@pytest.fixture
def post(monkeypatch):
    fake = FakePost()
    monkeypatch.setattr("src.clients.voice.httpx.post", fake)
    return fake


def write_wav(path, channels=1, sample_width=2, frame_rate=24000, frames=2400):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(frame_rate)
        wav.writeframes(b"\x00" * frames * channels * sample_width)


@pytest.fixture
def wav_file(tmp_path):
    path = tmp_path / "note.wav"
    write_wav(path)
    return str(path)


def transcribe(path, client, response=None):
    return transcribe_voice(path, client=client)


def test_success_returns_text_and_none_confidence(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "je suis en série D", "audioDurationMs": 100})
    assert transcribe(wav_file, client) == {"text": "je suis en série D", "confidence": None}


def test_present_confidence_is_returned(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "bonjour", "confidence": 0.9})
    assert transcribe(wav_file, client)["confidence"] == 0.9


def test_api_error_raises_typed_error(wav_file, client, post):
    post.response = FakeResponse(status_code=400, body={"error": "bad audio"})
    with pytest.raises(TranscriptionError, match="400"):
        transcribe(wav_file, client)


def test_network_failure_raises_typed_error(wav_file, client, post):
    post.error = httpx.ConnectError("connection refused")
    with pytest.raises(TranscriptionError, match="request failed"):
        transcribe(wav_file, client)


def test_empty_transcript_is_an_error_not_a_success(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "   "})
    with pytest.raises(TranscriptionError, match="empty transcript"):
        transcribe(wav_file, client)


def test_missing_transcript_is_an_error(wav_file, client, post):
    post.response = FakeResponse(body={"audioDurationMs": 100})
    with pytest.raises(TranscriptionError, match="empty transcript"):
        transcribe(wav_file, client)


def test_request_sends_model_language_and_keywords(wav_file, client, post):
    transcribe(wav_file, client)
    _, kwargs = post.calls[0]
    assert kwargs["timeout"] > 0
    request = json.loads(kwargs["files"]["request"][1])
    assert request["model"] == "muse-voice-transcribe-1.0"
    assert request["audioEncoding"] == "WAV"
    assert request["languageBias"] == ["French"]
    assert "série D" in request["keywords"]
    assert kwargs["files"]["audio"][2] == "audio/wav"


def test_number_words_are_normalized_to_digits(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "j'ai eu quatorze de moyenne"})
    assert transcribe(wav_file, client)["text"] == "j'ai eu 14 de moyenne"


def test_number_word_variants_are_normalized(wav_file, client, post):
    post.response = FakeResponse(body={"transcript": "Dix-sept en SVT et vingt en EPS"})
    assert transcribe(wav_file, client)["text"] == "17 en SVT et 20 en EPS"


def test_empty_audio_file_raises_before_any_call(tmp_path, client, post):
    path = tmp_path / "empty.wav"
    path.write_bytes(b"")
    with pytest.raises(TranscriptionError, match="empty"):
        transcribe(str(path), client)
    assert post.calls == []


def test_unsupported_format_raises_before_any_call(tmp_path, client, post):
    path = tmp_path / "note.txt"
    path.write_bytes(b"not audio")
    with pytest.raises(TranscriptionError, match="unsupported audio type"):
        transcribe(str(path), client)
    assert post.calls == []


def test_oversize_audio_raises_before_any_call(tmp_path, client, post):
    path = tmp_path / "huge.wav"
    with open(path, "wb") as handle:
        handle.seek(MAX_AUDIO_BYTES)
        handle.write(b"x")
    with pytest.raises(TranscriptionError, match="too large"):
        transcribe(str(path), client)
    assert post.calls == []


def test_missing_file_raises_typed_error(client, post):
    with pytest.raises(TranscriptionError, match="not found"):
        transcribe("nope.wav", client)
    assert post.calls == []


def test_invalid_wav_content_raises_before_any_call(tmp_path, client, post):
    path = tmp_path / "fake.wav"
    path.write_bytes(b"this is not a wav file")
    with pytest.raises(TranscriptionError, match="WAV"):
        transcribe(str(path), client)
    assert post.calls == []


def test_stereo_wav_raises_before_any_call(tmp_path, client, post):
    path = tmp_path / "stereo.wav"
    write_wav(path, channels=2)
    with pytest.raises(TranscriptionError, match="mono"):
        transcribe(str(path), client)
    assert post.calls == []


def test_too_long_audio_raises_before_any_call(wav_file, client, post, monkeypatch):
    import src.tools.transcribe_voice as tool

    monkeypatch.setattr(tool, "MAX_DURATION_SECONDS", 0)
    with pytest.raises(TranscriptionError, match="too long"):
        transcribe(wav_file, client)
    assert post.calls == []


def test_mp3_is_converted_before_transcribing(tmp_path, client, post, monkeypatch):
    import src.clients.voice as voice

    wav_path = tmp_path / "note.wav"
    write_wav(wav_path)
    wav_bytes = wav_path.read_bytes()
    converted = []

    def fake_convert(source, target):
        converted.append((source, target))
        target.write_bytes(wav_bytes)

    monkeypatch.setattr("src.tools.transcribe_voice.convert_to_wav", fake_convert)
    mp3_path = tmp_path / "note.mp3"
    mp3_path.write_bytes(b"fake mp3 bytes")
    assert transcribe(str(mp3_path), client)["text"] == "bonjour"
    assert len(converted) == 1
    assert post.calls != []
