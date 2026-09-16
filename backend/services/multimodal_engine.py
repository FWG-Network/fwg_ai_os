"""
Multimodal Engine — text/image/audio → semantic result.

4F-4 contract:
- Real modality inference succeeds -> return the real result.
- Modality import/model/file/inference failure -> raise explicitly.
- No hash/deterministic fallback is presented as a real embedding.
- No silent omission of requested audio results.
"""

from typing import Optional

from backend.core.logger import log


class MultimodalEngineError(RuntimeError):
    """Explicit multimodal processing failure."""


class MultimodalEngine:
    """Processes text/image/audio using real model-backed inference."""

    def __init__(self):
        self._clip_model = None
        self._clip_preprocess = None
        self._whisper = None

    # — Text Encoder ——————————
    def _encode_text(self, text: str) -> list:
        """Use the canonical real AIOS text embedding service."""
        try:
            from backend.llm.embedding_service import embedding_service

            embedding = embedding_service.encode(text)
            return (
                embedding.tolist()
                if hasattr(embedding, "tolist")
                else list(embedding)
            )
        except Exception as exc:
            log.error(f"[Multimodal] Text encoding failed: {exc}")
            raise MultimodalEngineError(
                f"text encoding failed: {exc}"
            ) from exc

    # — Image Encoder ——————————
    def _encode_image(self, image_path: str) -> list:
        """Real CLIP image embedding; never falls back to a hash."""
        try:
            import torch
            import clip
            from PIL import Image

            if self._clip_model is None:
                self._clip_model, self._clip_preprocess = clip.load(
                    "ViT-B/32",
                    device="cpu",
                )
                log.info("[Multimodal] ✅ CLIP loaded")

            image = self._clip_preprocess(Image.open(image_path)).unsqueeze(0)

            with torch.no_grad():
                features = self._clip_model.encode_image(image)

            return features.squeeze().tolist()

        except Exception as exc:
            log.error(f"[Multimodal] Image encoding failed: {exc}")
            raise MultimodalEngineError(
                f"image encoding failed: {exc}"
            ) from exc

    # — Audio Transcriber ——————————
    def _transcribe_audio(self, audio_path: str) -> str:
        """Real Whisper transcription; never silently returns None."""
        try:
            import whisper

            if self._whisper is None:
                self._whisper = whisper.load_model("base", device="cpu")
                log.info("[Multimodal] ✅ Whisper loaded")

            result = self._whisper.transcribe(audio_path)
            transcript = result.get("text", "").strip()

            if not transcript:
                raise MultimodalEngineError(
                    "audio transcription produced no transcript"
                )

            return transcript

        except MultimodalEngineError:
            raise
        except Exception as exc:
            log.error(f"[Multimodal] Audio transcription failed: {exc}")
            raise MultimodalEngineError(
                f"audio transcription failed: {exc}"
            ) from exc

    # — MAIN analyze ——————————
    async def analyze(
        self,
        text: Optional[str] = None,
        image_url: Optional[str] = None,
        task: str = "analyze",
    ) -> dict:
        """Endpoint interface backed by the real processing path."""
        return self.process(text=text, image_path=image_url)

    # — MAIN process ——————————
    def process(
        self,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
    ) -> dict:
        """Process supplied modalities using real inference only."""
        result = {}
        combined = []

        if text:
            log.info(f"[Multimodal] Encoding text: ({len(text)} chars)")
            embedding = self._encode_text(text)
            result["text_embedding"] = embedding
            combined = embedding

        if image_path:
            log.info(f"[Multimodal] Encoding image: {image_path}")
            embedding = self._encode_image(image_path)
            result["image_embedding"] = embedding
            combined = embedding

        if audio_path:
            log.info(f"[Multimodal] Transcribing audio: {audio_path}")
            transcript = self._transcribe_audio(audio_path)
            result["speech_to_text"] = transcript

            speech_embedding = self._encode_text(transcript)
            result["speech_embedding"] = speech_embedding
            combined = speech_embedding

        if combined:
            result["embedding"] = combined

        return result


# — Global instance ——————————
multimodal_engine_service = MultimodalEngine()
