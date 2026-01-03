"""JARVIS Voice Processing Service - Main FastAPI Application."""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .transcribe import get_transcribe_client, TranscribeClient
from .polly import get_polly_client, PollyClient, JARVIS_VOICE_PRESETS
from .streaming import handle_voice_websocket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.service_name}")
    yield
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Voice Processing Service",
    description="Speech-to-text and text-to-speech processing with AWS Transcribe and Polly",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class TranscriptionRequest(BaseModel):
    language_code: str = "en-US"


class TranscriptionResponse(BaseModel):
    text: str
    confidence: float
    is_final: bool
    processing_time_ms: int


class SynthesisRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    preset: Optional[str] = "default"
    use_ssml: bool = False
    output_format: str = "mp3"


class SynthesisResponse(BaseModel):
    audio_url: str
    content_type: str
    duration_estimate_ms: int
    characters: int


class VoiceInfo(BaseModel):
    id: str
    name: str
    gender: str
    language_code: str
    language_name: str


# Auth dependency
async def get_current_user(request: Request) -> dict:
    """Extract user from JWT token."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return {"user_id": payload.get("userId")}
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    language_code: str = Form("en-US"),
    user: dict = Depends(get_current_user),
    transcribe: TranscribeClient = Depends(get_transcribe_client)
):
    """
    Transcribe uploaded audio file to text.

    Accepts PCM, WAV, MP3, or other supported formats.
    """
    import time
    start_time = time.time()

    # Validate file size
    audio_data = await audio.read()
    if len(audio_data) > settings.max_audio_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Audio file too large. Maximum size: {settings.max_audio_size_bytes} bytes"
        )

    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        result = await transcribe.transcribe_audio(audio_data, language_code)

        processing_time = int((time.time() - start_time) * 1000)

        logger.info(
            f"Transcription completed",
            extra={
                "user_id": user["user_id"],
                "text_length": len(result["text"]),
                "processing_time_ms": processing_time
            }
        )

        return TranscriptionResponse(
            text=result["text"],
            confidence=result["confidence"],
            is_final=result["is_final"],
            processing_time_ms=processing_time
        )

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")


@app.post("/synthesize")
async def synthesize_speech(
    request: SynthesisRequest,
    user: dict = Depends(get_current_user),
    polly: PollyClient = Depends(get_polly_client)
):
    """
    Synthesize speech from text.

    Returns audio stream in the requested format.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # Get voice settings from preset
    preset = JARVIS_VOICE_PRESETS.get(request.preset, JARVIS_VOICE_PRESETS["default"])
    voice_id = request.voice_id or preset["voice_id"]

    try:
        # Optionally wrap in SSML
        text = request.text
        if request.use_ssml and not text.strip().startswith("<speak>"):
            text = polly.create_jarvis_ssml(
                text,
                emphasis=preset.get("emphasis", "moderate"),
                rate=preset.get("rate", "medium")
            )

        result = await polly.synthesize_speech(
            text=text,
            voice_id=voice_id,
            output_format=request.output_format,
            engine=preset.get("engine", "neural")
        )

        logger.info(
            f"Speech synthesized",
            extra={
                "user_id": user["user_id"],
                "text_length": len(request.text),
                "audio_size": len(result["audio_data"])
            }
        )

        # Return as streaming response
        return StreamingResponse(
            iter([result["audio_data"]]),
            media_type=result["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="speech.{request.output_format}"',
                "X-Characters-Synthesized": str(result["request_characters"]),
                "X-Voice-Id": voice_id
            }
        )

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(status_code=500, detail="Speech synthesis failed")


@app.get("/voices", response_model=list[VoiceInfo])
async def list_voices(
    language_code: Optional[str] = None,
    engine: Optional[str] = "neural",
    user: dict = Depends(get_current_user),
    polly: PollyClient = Depends(get_polly_client)
):
    """List available Polly voices."""
    try:
        voices = await polly.list_voices(language_code=language_code, engine=engine)
        return [VoiceInfo(**v) for v in voices]
    except Exception as e:
        logger.error(f"List voices error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list voices")


@app.get("/presets")
async def list_presets():
    """List available JARVIS voice presets."""
    return {
        "presets": list(JARVIS_VOICE_PRESETS.keys()),
        "details": JARVIS_VOICE_PRESETS
    }


def get_user_from_token(token: str) -> Optional[dict]:
    """Extract user from JWT token without raising exceptions."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return {"user_id": payload.get("userId")}
    except JWTError:
        return None


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket, token: str = None):
    """
    WebSocket endpoint for real-time voice streaming.

    Protocol:
    - Connect with token query parameter for authentication
    - Send {"type": "start"} to begin transcription
    - Send binary audio chunks (16-bit PCM, 16kHz, mono)
    - Send {"type": "stop"} to end and get final transcript
    - Send {"type": "synthesize", "text": "..."} for TTS response
    - Receive {"type": "partial", "text": "..."} for partial transcripts
    - Receive {"type": "final", "text": "..."} for final transcripts
    - Receive binary audio for synthesized speech
    """
    # Authenticate
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    user = get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    await websocket.accept()

    try:
        await handle_voice_websocket(websocket, user["user_id"])
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected for user {user['user_id']}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
