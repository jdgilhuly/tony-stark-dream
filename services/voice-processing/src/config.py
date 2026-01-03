from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Service
    service_name: str = "voice-processing"
    host: str = "0.0.0.0"
    port: int = 8002
    debug: bool = False

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # AWS Transcribe
    transcribe_language_code: str = "en-US"
    transcribe_sample_rate: int = 16000
    transcribe_media_encoding: str = "pcm"

    # AWS Polly
    polly_voice_id: str = "Brian"
    polly_engine: str = "neural"
    polly_output_format: str = "mp3"
    polly_sample_rate: str = "24000"

    # S3
    s3_audio_bucket: str = "jarvis-audio"
    s3_audio_prefix: str = "voice/"

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
