import json
import logging
from typing import AsyncGenerator
from abc import ABC, abstractmethod

import httpx

from .config import get_settings
from .models import Message, MessageRole

logger = logging.getLogger(__name__)
settings = get_settings()


class QuotaExceededError(Exception):
    """Raised when API quota/credits are exhausted."""
    pass


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate_response(
        self,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int = None
    ) -> tuple[str, dict]:
        """Generate a response from the LLM."""
        pass


class OpenAIClient(LLMClient):
    """Client for OpenAI API."""

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def generate_response(
        self,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int = None
    ) -> tuple[str, dict]:
        """Generate a response using OpenAI API."""
        max_tokens = max_tokens or settings.openai_max_tokens

        # Convert messages to OpenAI format
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if msg.role != MessageRole.SYSTEM:
                openai_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=openai_messages
            )

            # Extract text from response
            response_text = response.choices[0].message.content or ""

            usage = {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0
            }

            logger.info(
                f"OpenAI response generated",
                extra={
                    "model": self.model,
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens")
                }
            )

            return response_text, usage

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            # Check for quota exceeded error
            error_str = str(e)
            if "insufficient_quota" in error_str or "exceeded your current quota" in error_str:
                raise QuotaExceededError(
                    "OpenAI API quota exceeded. Please add credits at https://platform.openai.com/account/billing"
                )
            raise


class OllamaClient(LLMClient):
    """Client for local Ollama LLM."""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate_response(
        self,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int = None
    ) -> tuple[str, dict]:
        """Generate a response using Ollama."""
        max_tokens = max_tokens or settings.ollama_max_tokens

        # Convert messages to Ollama format
        ollama_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if msg.role != MessageRole.SYSTEM:
                ollama_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        request_body = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens
            }
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=request_body
            )
            response.raise_for_status()
            response_data = response.json()

            # Extract text from response
            response_text = response_data.get("message", {}).get("content", "")

            # Ollama provides token counts in eval_count and prompt_eval_count
            usage = {
                "input_tokens": response_data.get("prompt_eval_count", 0),
                "output_tokens": response_data.get("eval_count", 0)
            }

            logger.info(
                f"Ollama response generated",
                extra={
                    "model": self.model,
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens")
                }
            )

            return response_text, usage

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise


# Singleton instance
_llm_client: LLMClient | None = None


def get_bedrock_client() -> LLMClient:
    """Get the configured LLM client (Ollama or OpenAI)."""
    global _llm_client
    if _llm_client is None:
        if settings.llm_provider == "openai" and settings.openai_api_key:
            logger.info("Using OpenAI API for LLM")
            _llm_client = OpenAIClient()
        else:
            # Default to Ollama for local LLM
            logger.info(f"Using Ollama for LLM (model: {settings.ollama_model})")
            _llm_client = OllamaClient()
    return _llm_client
