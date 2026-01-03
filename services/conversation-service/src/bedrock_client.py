import json
import logging
from typing import AsyncGenerator
import boto3
from botocore.config import Config

from .config import get_settings
from .models import BedrockMessage, Message, MessageRole

logger = logging.getLogger(__name__)
settings = get_settings()


class BedrockClient:
    """Client for AWS Bedrock Claude API."""

    def __init__(self):
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
        """
        Generate a response using Claude via Bedrock.

        Returns:
            Tuple of (response_text, usage_info)
        """
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

    async def generate_response_stream(
        self,
        messages: list[Message],
        system_prompt: str,
        max_tokens: int = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using Claude via Bedrock.

        Yields text chunks as they arrive.
        """
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
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )

            stream = response.get("body")
            if stream:
                for event in stream:
                    chunk = event.get("chunk")
                    if chunk:
                        chunk_data = json.loads(chunk.get("bytes").decode())

                        if chunk_data.get("type") == "content_block_delta":
                            delta = chunk_data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")

        except Exception as e:
            logger.error(f"Bedrock streaming error: {e}")
            raise


# Singleton instance
_bedrock_client: BedrockClient | None = None


def get_bedrock_client() -> BedrockClient:
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient()
    return _bedrock_client
