import pytest

from backend.services.multimodal_engine import (
    MultimodalEngine,
    MultimodalEngineError,
)


def test_image_failure_is_explicit(monkeypatch):
    engine = MultimodalEngine()

    def fail(_path):
        raise MultimodalEngineError("image encoding failed: test")

    monkeypatch.setattr(engine, "_encode_image", fail)

    with pytest.raises(MultimodalEngineError, match="image encoding failed"):
        engine.process(image_path="/tmp/missing-image.png")


def test_audio_failure_is_explicit(monkeypatch):
    engine = MultimodalEngine()

    def fail(_path):
        raise MultimodalEngineError("audio transcription failed: test")

    monkeypatch.setattr(engine, "_transcribe_audio", fail)

    with pytest.raises(MultimodalEngineError, match="audio transcription failed"):
        engine.process(audio_path="/tmp/missing-audio.wav")


def test_audio_empty_transcript_is_failure(monkeypatch):
    engine = MultimodalEngine()

    class FakeWhisper:
        def transcribe(self, _path):
            return {"text": "   "}

    engine._whisper = FakeWhisper()

    with pytest.raises(
        MultimodalEngineError,
        match="no transcript",
    ):
        engine._transcribe_audio("/tmp/empty.wav")


def test_text_failure_is_explicit(monkeypatch):
    engine = MultimodalEngine()

    def fail(_text):
        raise MultimodalEngineError("text encoding failed: test")

    monkeypatch.setattr(engine, "_encode_text", fail)

    with pytest.raises(MultimodalEngineError, match="text encoding failed"):
        engine.process(text="real text")


def test_success_path_preserves_real_results(monkeypatch):
    engine = MultimodalEngine()

    monkeypatch.setattr(engine, "_encode_text", lambda _text: [1.0, 2.0, 3.0])
    monkeypatch.setattr(engine, "_encode_image", lambda _path: [4.0, 5.0, 6.0])

    result = engine.process(
        text="hello",
        image_path="/tmp/real.png",
    )

    assert result["text_embedding"] == [1.0, 2.0, 3.0]
    assert result["image_embedding"] == [4.0, 5.0, 6.0]
    assert result["embedding"] == [4.0, 5.0, 6.0]
