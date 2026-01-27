"""Local Whisper integration for speech-to-text."""

import asyncio
import logging
import tempfile
import os
from typing import AsyncGenerator

import whisper
import numpy as np

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TranscribeClient:
    """Client for local Whisper speech-to-text transcription."""

    def __init__(self):
        logger.info(f"Loading Whisper model: {settings.whisper_model}")
        self.model = whisper.load_model(
            settings.whisper_model,
            device=settings.whisper_device
        )
        self.language = settings.whisper_language
        logger.info("Whisper model loaded successfully")

    async def transcribe_audio(
        self,
        audio_data: bytes,
        language_code: str = None
    ) -> dict:
        """
        Transcribe audio data using Whisper.

        Args:
            audio_data: Raw audio bytes (WAV, MP3, PCM, or other supported format)
            language_code: Language code (default from settings)

        Returns:
            Transcription result with text and confidence
        """
        language = language_code.split("-")[0] if language_code else self.language

        # Write audio to temp file for Whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    temp_path,
                    language=language,
                    fp16=False  # Use fp32 for CPU
                )
            )

            text = result.get("text", "").strip()

            # Whisper doesn't provide per-word confidence, estimate from segments
            segments = result.get("segments", [])
            if segments:
                avg_no_speech_prob = sum(s.get("no_speech_prob", 0) for s in segments) / len(segments)
                confidence = 1.0 - avg_no_speech_prob
            else:
                confidence = 0.9 if text else 0.0

            logger.info(
                f"Transcription completed",
                extra={
                    "text_length": len(text),
                    "confidence": confidence,
                    "language": language
                }
            )

            return {
                "text": text,
                "confidence": confidence,
                "is_final": True
            }

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise

        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass


class StreamingTranscriber:
    """Buffered streaming transcription using Whisper."""

    def __init__(self):
        self.transcriber = TranscribeClient()
        self.sample_rate = 16000  # Whisper expects 16kHz

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language_code: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        Stream audio for transcription.

        Note: Whisper doesn't support true streaming, so we buffer chunks
        and transcribe periodically.

        Args:
            audio_stream: Async generator yielding audio chunks
            language_code: Language code (default from settings)

        Yields:
            Partial and final transcription results
        """
        buffer = bytearray()
        chunk_size = self.sample_rate * 2 * 2  # 2 seconds of 16-bit audio

        async for chunk in audio_stream:
            buffer.extend(chunk)

            # Transcribe when we have enough audio
            if len(buffer) >= chunk_size:
                try:
                    result = await self.transcriber.transcribe_audio(
                        bytes(buffer),
                        language_code
                    )
                    yield {
                        "text": result["text"],
                        "confidence": result["confidence"],
                        "is_final": False
                    }
                except Exception as e:
                    logger.error(f"Streaming transcription error: {e}")

        # Final transcription of remaining buffer
        if buffer:
            try:
                result = await self.transcriber.transcribe_audio(
                    bytes(buffer),
                    language_code
                )
                yield {
                    "text": result["text"],
                    "confidence": result["confidence"],
                    "is_final": True
                }
            except Exception as e:
                logger.error(f"Final transcription error: {e}")
                yield {"text": "", "confidence": 0.0, "is_final": True}


# Singleton instance
_transcribe_client: TranscribeClient | None = None


def get_transcribe_client() -> TranscribeClient:
    global _transcribe_client
    if _transcribe_client is None:
        _transcribe_client = TranscribeClient()
    return _transcribe_client
