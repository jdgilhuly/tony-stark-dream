"""Local text-to-speech using espeak-ng directly."""

import asyncio
import logging
import tempfile
import subprocess
import os
import re
from typing import Optional

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PollyClient:
    """Client for local text-to-speech synthesis using espeak-ng."""

    def __init__(self):
        logger.info("Initializing espeak-ng TTS engine")
        self.rate = settings.tts_rate
        self.voice = "en-gb"  # Default British English voice (JARVIS-like)

        # Get available voices
        try:
            result = subprocess.run(
                ["espeak-ng", "--voices"],
                capture_output=True,
                text=True
            )
            # Parse voices from output
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            self.voices = []
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    self.voices.append({
                        "id": parts[4] if len(parts) > 4 else parts[1],
                        "name": parts[4] if len(parts) > 4 else parts[1],
                        "language": parts[1]
                    })
        except Exception as e:
            logger.warning(f"Could not list voices: {e}")
            self.voices = [{"id": "en", "name": "English", "language": "en"}]

        logger.info(f"espeak-ng initialized with {len(self.voices)} voices available")

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
        Synthesize speech from text using espeak-ng.

        Args:
            text: Text to synthesize (SSML tags will be stripped)
            voice_id: Voice name (optional)
            output_format: Output format (only wav supported locally)
            engine: Ignored
            sample_rate: Ignored

        Returns:
            Dict with audio_data, content_type, and metadata
        """
        # Strip SSML if present
        clean_text = self._strip_ssml(text)

        if not clean_text:
            raise ValueError("Text is empty after processing")

        # Select voice
        voice = voice_id if voice_id else self.voice

        try:
            # Run espeak-ng in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None,
                lambda: self._synthesize_with_espeak(clean_text, voice)
            )

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
                "voice_id": voice,
                "format": "wav"
            }

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            raise

    def _synthesize_with_espeak(self, text: str, voice: str) -> bytes:
        """Synchronous helper to synthesize text using espeak-ng."""
        # Use espeak-ng to output WAV to stdout
        result = subprocess.run(
            [
                "espeak-ng",
                "-v", voice,
                "-s", str(self.rate),
                "--stdout",
                text
            ],
            capture_output=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"espeak-ng failed: {result.stderr.decode()}")

        return result.stdout

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
        List available espeak-ng voices.

        Args:
            language_code: Filter by language (optional, partial match)
            engine: Ignored

        Returns:
            List of voice info dicts
        """
        result = []
        for i, voice in enumerate(self.voices):
            voice_lang = voice.get("language", "en")

            # Filter by language if specified
            if language_code and language_code.lower() not in voice_lang.lower():
                continue

            result.append({
                "id": voice.get("id", str(i)),
                "name": voice.get("name", f"Voice {i}"),
                "gender": "unknown",
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

        Note: This is kept for API compatibility but espeak-ng doesn't use SSML.
        The rate adjustment is applied via espeak-ng -s flag instead.

        Args:
            text: Plain text
            emphasis: Ignored
            rate: Speaking rate (adjusts espeak rate)

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
            self.rate = rate_map[rate]

        return text


# JARVIS voice presets (adapted for espeak-ng)
JARVIS_VOICE_PRESETS = {
    "default": {
        "voice_id": "en-gb",  # British English (JARVIS-like)
        "engine": "local",
        "rate": "medium",
        "emphasis": "moderate"
    },
    "urgent": {
        "voice_id": "en-gb",
        "engine": "local",
        "rate": "fast",
        "emphasis": "strong"
    },
    "calm": {
        "voice_id": "en-gb",
        "engine": "local",
        "rate": "slow",
        "emphasis": "reduced"
    },
    "formal": {
        "voice_id": "en-gb-x-rp",  # Received Pronunciation
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
