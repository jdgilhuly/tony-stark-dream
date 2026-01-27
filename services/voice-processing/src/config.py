from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Service
    service_name: str = "voice-processing"
    host: str = "0.0.0.0"
    port: int = 8002
    debug: bool = False

    # Authentication
    auth_disabled: bool = False  # Set AUTH_DISABLED=true to bypass auth

    # Whisper (local speech-to-text)
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_language: str = "en"

    # pyttsx3 (local text-to-speech)
    tts_engine: str = "pyttsx3"
    tts_rate: int = 150
    tts_voice_index: int = 0  # Index into system voices

    # JWT
    jwt_secret: str = "development-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    # Limits
    max_audio_duration_seconds: int = 60
    max_audio_size_bytes: int = 10 * 1024 * 1024  # 10MB

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
