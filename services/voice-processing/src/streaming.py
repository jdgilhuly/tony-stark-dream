"""WebSocket streaming handlers for real-time voice processing."""

import logging
import asyncio
import json
from typing import Optional, AsyncGenerator
from datetime import datetime

import boto3
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TranscriptionHandler(TranscriptResultStreamHandler):
    """Handler for processing transcription results."""

    def __init__(self, output_stream, websocket):
        super().__init__(output_stream)
        self.websocket = websocket
        self.transcript_parts = []
        self.final_transcript = ""

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """Handle incoming transcription events."""
        results = transcript_event.transcript.results

        for result in results:
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript

            if result.is_partial:
                # Send partial result
                await self.websocket.send_json({
                    "type": "partial",
                    "text": transcript,
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                # Final result for this segment
                self.transcript_parts.append(transcript)
                self.final_transcript = " ".join(self.transcript_parts)

                await self.websocket.send_json({
                    "type": "final",
                    "text": self.final_transcript,
                    "segment": transcript,
                    "timestamp": datetime.utcnow().isoformat()
                })


async def stream_transcription(websocket, audio_stream: AsyncGenerator[bytes, None]):
    """
    Stream audio to AWS Transcribe and return transcription results.

    Args:
        websocket: WebSocket connection to send results to
        audio_stream: Async generator yielding audio chunks
    """
    client = TranscribeStreamingClient(region=settings.aws_region)

    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )

    handler = TranscriptionHandler(stream.output_stream, websocket)

    async def write_chunks():
        """Write audio chunks to the transcription stream."""
        async for chunk in audio_stream:
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
        await stream.input_stream.end_stream()

    # Run transcription and chunk writing concurrently
    await asyncio.gather(
        write_chunks(),
        handler.handle_events(),
    )

    return handler.final_transcript


async def synthesize_speech_stream(
    text: str,
    voice_id: str = "Brian",
    engine: str = "neural"
) -> AsyncGenerator[bytes, None]:
    """
    Stream synthesized speech from AWS Polly.

    Args:
        text: Text to synthesize
        voice_id: Polly voice ID
        engine: Polly engine (standard or neural)

    Yields:
        Audio chunks in MP3 format
    """
    polly = boto3.client(
        "polly",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    # Add JARVIS-style SSML if not already present
    if not text.startswith("<speak>"):
        ssml_text = f"""
        <speak>
            <prosody rate="medium" pitch="low">
                {text}
            </prosody>
        </speak>
        """
    else:
        ssml_text = text

    response = polly.synthesize_speech(
        Text=ssml_text,
        TextType="ssml",
        OutputFormat="mp3",
        VoiceId=voice_id,
        Engine=engine,
    )

    # Stream the audio
    audio_stream = response["AudioStream"]
    chunk_size = 4096

    while True:
        chunk = audio_stream.read(chunk_size)
        if not chunk:
            break
        yield chunk


class VoiceStreamingSession:
    """Manages a voice streaming session with bidirectional audio."""

    def __init__(self, websocket, user_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.is_active = True
        self.transcription_task: Optional[asyncio.Task] = None
        self.audio_queue: asyncio.Queue = asyncio.Queue()

    async def start(self):
        """Start the streaming session."""
        logger.info(f"Starting voice streaming session for user {self.user_id}")

        await self.websocket.send_json({
            "type": "session_started",
            "user_id": self.user_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def handle_audio_chunk(self, data: bytes):
        """Handle incoming audio chunk."""
        await self.audio_queue.put(data)

    async def audio_generator(self) -> AsyncGenerator[bytes, None]:
        """Generate audio chunks from the queue."""
        while self.is_active:
            try:
                chunk = await asyncio.wait_for(self.audio_queue.get(), timeout=5.0)
                yield chunk
            except asyncio.TimeoutError:
                # Check if session is still active
                if not self.is_active:
                    break

    async def start_transcription(self):
        """Start transcription with the queued audio."""
        try:
            transcript = await stream_transcription(
                self.websocket,
                self.audio_generator()
            )
            return transcript
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            return None

    async def synthesize_and_stream(self, text: str):
        """Synthesize speech and stream to client."""
        try:
            await self.websocket.send_json({
                "type": "synthesis_started",
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            })

            async for chunk in synthesize_speech_stream(text):
                await self.websocket.send_bytes(chunk)

            await self.websocket.send_json({
                "type": "synthesis_complete",
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

    async def stop(self):
        """Stop the streaming session."""
        self.is_active = False

        if self.transcription_task and not self.transcription_task.done():
            self.transcription_task.cancel()

        logger.info(f"Stopped voice streaming session for user {self.user_id}")

        await self.websocket.send_json({
            "type": "session_ended",
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_voice_websocket(websocket, user_id: str):
    """
    Handle a WebSocket connection for voice streaming.

    Protocol:
    - Client sends: {"type": "start"} to begin transcription
    - Client sends: binary audio chunks (16-bit PCM, 16kHz, mono)
    - Client sends: {"type": "stop"} to end transcription
    - Client sends: {"type": "synthesize", "text": "..."} for TTS
    - Server sends: {"type": "partial", "text": "..."} for partial transcripts
    - Server sends: {"type": "final", "text": "..."} for final transcripts
    - Server sends: binary audio chunks for synthesized speech
    """
    session = VoiceStreamingSession(websocket, user_id)
    await session.start()

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Audio data
                    await session.handle_audio_chunk(message["bytes"])

                elif "text" in message:
                    # JSON command
                    try:
                        data = json.loads(message["text"])
                        command = data.get("type")

                        if command == "start":
                            # Start transcription
                            session.transcription_task = asyncio.create_task(
                                session.start_transcription()
                            )

                        elif command == "stop":
                            # Stop transcription
                            await session.stop()
                            if session.transcription_task:
                                transcript = await session.transcription_task
                                if transcript:
                                    await websocket.send_json({
                                        "type": "transcription_complete",
                                        "text": transcript,
                                        "timestamp": datetime.utcnow().isoformat()
                                    })

                        elif command == "synthesize":
                            # Text-to-speech
                            text = data.get("text", "")
                            if text:
                                await session.synthesize_and_stream(text)

                        elif command == "ping":
                            await websocket.send_json({"type": "pong"})

                    except json.JSONDecodeError:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid JSON"
                        })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await session.stop()
