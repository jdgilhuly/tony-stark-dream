"""AWS Transcribe integration for speech-to-text."""

import asyncio
import logging
import uuid
from typing import AsyncGenerator
import boto3
from botocore.config import Config

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TranscribeClient:
    """Client for AWS Transcribe streaming and batch transcription."""

    def __init__(self):
        config = Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"}
        )

        self.client = boto3.client(
            "transcribe",
            config=config,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        self.streaming_client = boto3.client(
            "transcribe-streaming",
            config=config,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    async def transcribe_audio(
        self,
        audio_data: bytes,
        language_code: str = None
    ) -> dict:
        """
        Transcribe audio data using batch transcription.

        Args:
            audio_data: Raw audio bytes (PCM or other supported format)
            language_code: Language code (default: en-US)

        Returns:
            Transcription result with text and confidence
        """
        language_code = language_code or settings.transcribe_language_code
        job_name = f"jarvis-transcribe-{uuid.uuid4().hex[:8]}"

        # Upload audio to S3 first
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

        audio_key = f"{settings.s3_audio_prefix}input/{job_name}.pcm"
        s3.put_object(
            Bucket=settings.s3_audio_bucket,
            Key=audio_key,
            Body=audio_data
        )

        audio_uri = f"s3://{settings.s3_audio_bucket}/{audio_key}"

        try:
            # Start transcription job
            self.client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={"MediaFileUri": audio_uri},
                MediaFormat="pcm",
                MediaSampleRateHertz=settings.transcribe_sample_rate,
                LanguageCode=language_code,
                OutputBucketName=settings.s3_audio_bucket,
                OutputKey=f"{settings.s3_audio_prefix}output/{job_name}.json"
            )

            # Poll for completion
            while True:
                response = self.client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                status = response["TranscriptionJob"]["TranscriptionJobStatus"]

                if status == "COMPLETED":
                    # Get transcript from S3
                    transcript_obj = s3.get_object(
                        Bucket=settings.s3_audio_bucket,
                        Key=f"{settings.s3_audio_prefix}output/{job_name}.json"
                    )
                    import json
                    transcript_data = json.loads(transcript_obj["Body"].read())

                    results = transcript_data.get("results", {})
                    transcripts = results.get("transcripts", [])

                    if transcripts:
                        return {
                            "text": transcripts[0].get("transcript", ""),
                            "confidence": self._extract_confidence(results),
                            "is_final": True
                        }
                    return {"text": "", "confidence": 0.0, "is_final": True}

                elif status == "FAILED":
                    logger.error(f"Transcription failed: {response}")
                    raise Exception("Transcription job failed")

                await asyncio.sleep(0.5)

        finally:
            # Cleanup
            try:
                self.client.delete_transcription_job(TranscriptionJobName=job_name)
            except Exception:
                pass

    def _extract_confidence(self, results: dict) -> float:
        """Extract average confidence from transcription results."""
        items = results.get("items", [])
        if not items:
            return 0.0

        confidences = [
            float(item.get("alternatives", [{}])[0].get("confidence", 0))
            for item in items
            if item.get("alternatives")
        ]

        return sum(confidences) / len(confidences) if confidences else 0.0


class StreamingTranscriber:
    """WebSocket-based streaming transcription."""

    def __init__(self):
        self.config = Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"}
        )

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language_code: str = None
    ) -> AsyncGenerator[dict, None]:
        """
        Stream audio for real-time transcription.

        Args:
            audio_stream: Async generator yielding audio chunks
            language_code: Language code (default: en-US)

        Yields:
            Partial and final transcription results
        """
        language_code = language_code or settings.transcribe_language_code

        # Note: Full streaming implementation requires amazon-transcribe-streaming-sdk
        # This is a simplified version that buffers and transcribes

        buffer = bytearray()
        transcriber = TranscribeClient()

        async for chunk in audio_stream:
            buffer.extend(chunk)

            # Transcribe when we have enough audio (approx 1 second at 16kHz)
            if len(buffer) >= settings.transcribe_sample_rate * 2:
                try:
                    result = await transcriber.transcribe_audio(bytes(buffer))
                    yield {
                        "text": result["text"],
                        "confidence": result["confidence"],
                        "is_final": False
                    }
                except Exception as e:
                    logger.error(f"Streaming transcription error: {e}")

        # Final transcription
        if buffer:
            try:
                result = await transcriber.transcribe_audio(bytes(buffer))
                yield {
                    "text": result["text"],
                    "confidence": result["confidence"],
                    "is_final": True
                }
            except Exception as e:
                logger.error(f"Final transcription error: {e}")
                yield {"text": "", "confidence": 0.0, "is_final": True}


# Singleton instances
_transcribe_client: TranscribeClient | None = None


def get_transcribe_client() -> TranscribeClient:
    global _transcribe_client
    if _transcribe_client is None:
        _transcribe_client = TranscribeClient()
    return _transcribe_client
