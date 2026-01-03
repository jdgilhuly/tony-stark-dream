"""AWS Polly integration for text-to-speech."""

import logging
from typing import Optional
import boto3
from botocore.config import Config

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PollyClient:
    """Client for AWS Polly text-to-speech synthesis."""

    def __init__(self):
        config = Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"}
        )

        self.client = boto3.client(
            "polly",
            config=config,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

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
            text: Text to synthesize
            voice_id: Polly voice ID (default: Brian)
            output_format: Output format (mp3, ogg_vorbis, pcm)
            engine: Engine type (standard, neural)
            sample_rate: Sample rate for PCM output

        Returns:
            Dict with audio_data, content_type, and metadata
        """
        voice_id = voice_id or settings.polly_voice_id
        output_format = output_format or settings.polly_output_format
        engine = engine or settings.polly_engine
        sample_rate = sample_rate or settings.polly_sample_rate

        try:
            # Check if text contains SSML
            text_type = "ssml" if text.strip().startswith("<speak>") else "text"

            params = {
                "Text": text,
                "TextType": text_type,
                "VoiceId": voice_id,
                "OutputFormat": output_format,
                "Engine": engine,
            }

            # Add sample rate for PCM output
            if output_format == "pcm":
                params["SampleRate"] = sample_rate

            response = self.client.synthesize_speech(**params)

            audio_data = response["AudioStream"].read()

            logger.info(
                f"Synthesized speech",
                extra={
                    "voice_id": voice_id,
                    "text_length": len(text),
                    "audio_size": len(audio_data),
                    "content_type": response["ContentType"]
                }
            )

            return {
                "audio_data": audio_data,
                "content_type": response["ContentType"],
                "request_characters": response.get("RequestCharacters", len(text)),
                "voice_id": voice_id,
                "format": output_format
            }

        except Exception as e:
            logger.error(f"Polly synthesis error: {e}")
            raise

    async def synthesize_speech_ssml(
        self,
        ssml: str,
        voice_id: str = None,
        output_format: str = None,
        engine: str = None
    ) -> dict:
        """
        Synthesize speech from SSML.

        Args:
            ssml: SSML markup (must start with <speak>)
            voice_id: Polly voice ID
            output_format: Output format
            engine: Engine type

        Returns:
            Dict with audio_data and metadata
        """
        if not ssml.strip().startswith("<speak>"):
            ssml = f"<speak>{ssml}</speak>"

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
        List available Polly voices.

        Args:
            language_code: Filter by language (e.g., 'en-US')
            engine: Filter by engine type

        Returns:
            List of voice info dicts
        """
        params = {}
        if language_code:
            params["LanguageCode"] = language_code
        if engine:
            params["Engine"] = engine

        response = self.client.describe_voices(**params)

        return [
            {
                "id": voice["Id"],
                "name": voice["Name"],
                "gender": voice["Gender"],
                "language_code": voice["LanguageCode"],
                "language_name": voice["LanguageName"],
                "supported_engines": voice.get("SupportedEngines", [])
            }
            for voice in response.get("Voices", [])
        ]

    def create_jarvis_ssml(
        self,
        text: str,
        emphasis: str = "moderate",
        rate: str = "medium"
    ) -> str:
        """
        Create SSML with JARVIS-appropriate speech characteristics.

        Args:
            text: Plain text to wrap in SSML
            emphasis: Speech emphasis level
            rate: Speaking rate

        Returns:
            SSML markup string
        """
        # Clean text for SSML
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&apos;")

        ssml = f"""<speak>
    <prosody rate="{rate}">
        <emphasis level="{emphasis}">
            {text}
        </emphasis>
    </prosody>
</speak>"""

        return ssml


# JARVIS voice presets
JARVIS_VOICE_PRESETS = {
    "default": {
        "voice_id": "Brian",
        "engine": "neural",
        "rate": "medium",
        "emphasis": "moderate"
    },
    "urgent": {
        "voice_id": "Brian",
        "engine": "neural",
        "rate": "fast",
        "emphasis": "strong"
    },
    "calm": {
        "voice_id": "Brian",
        "engine": "neural",
        "rate": "slow",
        "emphasis": "reduced"
    },
    "formal": {
        "voice_id": "Brian",
        "engine": "neural",
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
