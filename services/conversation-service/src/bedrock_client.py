import json
import logging
from typing import AsyncGenerator
from abc import ABC, abstractmethod

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


class BedrockClient(LLMClient):
    """Client for AWS Bedrock Claude API."""

    def __init__(self):
        import boto3
        from botocore.config import Config

        config = Config(
            region_name=settings.aws_region,
            retries={"max_attempts": 3, "mode": "adaptive"}
        )

        self.client = boto3.client(
            "bedrock-runtime",
            config=config,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self.model_id = settings.bedrock_model_id

    async def generate_response(
        self,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int = None
    ) -> tuple[str, dict]:
        """Generate a response using Claude via Bedrock."""
        max_tokens = max_tokens or settings.bedrock_max_tokens

        # Convert messages to Bedrock format
        bedrock_messages = []
        for msg in messages:
            if msg.role != MessageRole.SYSTEM:
                bedrock_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": bedrock_messages
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())

            # Extract text from response
            content = response_body.get("content", [])
            response_text = ""
            for block in content:
                if block.get("type") == "text":
                    response_text += block.get("text", "")

            usage = response_body.get("usage", {})

            logger.info(
                f"Bedrock response generated",
                extra={
                    "model": self.model_id,
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens")
                }
            )

            return response_text, usage

        except Exception as e:
            logger.error(f"Bedrock API error: {e}")
            raise


# Singleton instance
_llm_client: LLMClient | None = None


def get_bedrock_client() -> LLMClient:
    """Get the configured LLM client (OpenAI or Bedrock)."""
    global _llm_client
    if _llm_client is None:
        if settings.llm_provider == "openai" and settings.openai_api_key:
            logger.info("Using OpenAI API for LLM")
            _llm_client = OpenAIClient()
        elif settings.aws_access_key_id and settings.aws_secret_access_key:
            logger.info("Using AWS Bedrock for LLM")
            _llm_client = BedrockClient()
        else:
            raise ValueError(
                "No LLM provider configured. Set OPENAI_API_KEY or AWS credentials."
            )
    return _llm_client
