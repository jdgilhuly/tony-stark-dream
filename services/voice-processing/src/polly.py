"""Local text-to-speech using pyttsx3."""

import asyncio
import logging
import tempfile
import os
import re
from typing import Optional

import pyttsx3

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PollyClient:
    """Client for local text-to-speech synthesis using pyttsx3."""

    def __init__(self):
        logger.info("Initializing pyttsx3 TTS engine")
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', settings.tts_rate)

        # Get available voices
        self.voices = self.engine.getProperty('voices')
        if self.voices and settings.tts_voice_index < len(self.voices):
            self.engine.setProperty('voice', self.voices[settings.tts_voice_index].id)

        logger.info(f"pyttsx3 initialized with {len(self.voices)} voices available")

    def _strip_ssml(self, text: str) -> str:
        """Remove SSML tags from text since pyttsx3 doesn't support SSML."""
        # Remove SSML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str = None,
        output_format: str = None,
        engine: str = None,
        sample_rate: str = None
    ) -> dict:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize (SSML tags will be stripped)
            voice_id: Voice index as string (optional)
            output_format: Output format (only wav supported locally)
            engine: Ignored (pyttsx3 uses system TTS)
            sample_rate: Ignored

        Returns:
            Dict with audio_data, content_type, and metadata
        """
        # Strip SSML if present
        clean_text = self._strip_ssml(text)

        if not clean_text:
            raise ValueError("Text is empty after processing")

        # Set voice if specified
        if voice_id:
            try:
                voice_idx = int(voice_id)
                if 0 <= voice_idx < len(self.voices):
                    self.engine.setProperty('voice', self.voices[voice_idx].id)
            except (ValueError, IndexError):
                pass  # Keep current voice

        # Create temp file for audio output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Run TTS in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._synthesize_to_file(clean_text, temp_path)
            )

            # Read the audio file
            with open(temp_path, 'rb') as f:
                audio_data = f.read()

            logger.info(
                f"Synthesized speech",
                extra={
                    "text_length": len(clean_text),
                    "audio_size": len(audio_data)
                }
            )

            return {
                "audio_data": audio_data,
                "content_type": "audio/wav",
                "request_characters": len(clean_text),
                "voice_id": str(settings.tts_voice_index),
                "format": "wav"
            }

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            raise

        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    def _synthesize_to_file(self, text: str, filepath: str):
        """Synchronous helper to synthesize text to file."""
        self.engine.save_to_file(text, filepath)
        self.engine.runAndWait()

    async def synthesize_speech_ssml(
        self,
        ssml: str,
        voice_id: str = None,
        output_format: str = None,
        engine: str = None
    ) -> dict:
        """
        Synthesize speech from SSML.

        Note: SSML tags are stripped since pyttsx3 doesn't support SSML.

        Args:
            ssml: SSML markup (tags will be removed)
            voice_id: Voice index as string
            output_format: Output format
            engine: Ignored

        Returns:
            Dict with audio_data and metadata
        """
        return await self.synthesize_speech(
            text=ssml,
            voice_id=voice_id,
            output_format=output_format,
            engine=engine
        )

    async def list_voices(
        self,
        language_code: str = None,
        engine: str = None
    ) -> list[dict]:
        """
        List available system voices.

        Args:
            language_code: Filter by language (optional, partial match)
            engine: Ignored

        Returns:
            List of voice info dicts
        """
        result = []
        for i, voice in enumerate(self.voices):
            # Extract language from voice properties
            voice_lang = getattr(voice, 'languages', ['en'])[0] if hasattr(voice, 'languages') else 'en'

            # Filter by language if specified
            if language_code and language_code.lower() not in voice_lang.lower():
                continue

            result.append({
                "id": str(i),
                "name": voice.name,
                "gender": getattr(voice, 'gender', 'unknown'),
                "language_code": voice_lang,
                "language_name": voice_lang,
                "supported_engines": ["local"]
            })

        return result

    def create_jarvis_ssml(
        self,
        text: str,
        emphasis: str = "moderate",
        rate: str = "medium"
    ) -> str:
        """
        Create SSML-like markup (will be stripped before synthesis).

        Note: This is kept for API compatibility but pyttsx3 doesn't use SSML.
        The rate adjustment is applied via engine settings instead.

        Args:
            text: Plain text
            emphasis: Ignored
            rate: Speaking rate (adjusts engine rate)

        Returns:
            Original text (SSML wrapper is ignored)
        """
        # Adjust rate based on parameter
        rate_map = {
            "slow": 100,
            "medium": 150,
            "fast": 200
        }
        if rate in rate_map:
            self.engine.setProperty('rate', rate_map[rate])

        return text


# JARVIS voice presets (adapted for local TTS)
JARVIS_VOICE_PRESETS = {
    "default": {
        "voice_id": "0",
        "engine": "local",
        "rate": "medium",
        "emphasis": "moderate"
    },
    "urgent": {
        "voice_id": "0",
        "engine": "local",
        "rate": "fast",
        "emphasis": "strong"
    },
    "calm": {
        "voice_id": "0",
        "engine": "local",
        "rate": "slow",
        "emphasis": "reduced"
    },
    "formal": {
        "voice_id": "0",
        "engine": "local",
        "rate": "medium",
        "emphasis": "moderate"
    }
}


# Singleton instance
_polly_client: PollyClient | None = None


def get_polly_client() -> PollyClient:
    global _polly_client
    if _polly_client is None:
        _polly_client = PollyClient()
    return _polly_client
