"""Memory service configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Memory service settings."""

    service_name: str = "memory-service"
    host: str = "0.0.0.0"
    port: int = 8011
    debug: bool = False

    # Security
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "jarvis_memories"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Memory settings
    max_memories_per_query: int = 10
    memory_decay_days: int = 365  # Memories older than this may be consolidated
    min_importance_threshold: float = 0.3

    # Entity extraction
    enable_entity_extraction: bool = True
    spacy_model: str = "en_core_web_sm"

    class Config:
        env_prefix = "MEMORY_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
