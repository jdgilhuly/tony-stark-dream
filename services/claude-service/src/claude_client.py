"""
Claude API Client

Provides a robust client for interacting with Claude API,
with support for streaming, tool use, and fallback to Ollama.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union

import anthropic
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """Message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class StopReason(str, Enum):
    """Stop reasons."""
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USE = "tool_use"


@dataclass
class Message:
    """A conversation message."""
    role: MessageRole
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ToolDefinition:
    """A tool definition for Claude."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[Callable] = None


@dataclass
class ToolResult:
    """Result of a tool call."""
    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass
class StreamChunk:
    """A chunk of streamed response."""
    type: str  # text, tool_use, stop
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_use_id: Optional[str] = None


@dataclass
class CompletionResponse:
    """A completion response."""
    content: str
    stop_reason: StopReason
    tool_calls: List[Dict[str, Any]]
    input_tokens: int
    output_tokens: int
    model: str
    latency_ms: float


class RateLimiter:
    """Simple rate limiter."""

    def __init__(self, requests_per_minute: int, tokens_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.request_times: List[float] = []
        self.token_counts: List[tuple] = []  # (timestamp, count)
        self._lock = asyncio.Lock()

    async def acquire(self, estimated_tokens: int = 1000) -> None:
        """Wait until rate limit allows request."""
        async with self._lock:
            now = time.time()
            minute_ago = now - 60

            # Clean old entries
            self.request_times = [t for t in self.request_times if t > minute_ago]
            self.token_counts = [(t, c) for t, c in self.token_counts if t > minute_ago]

            # Check request limit
            while len(self.request_times) >= self.requests_per_minute:
                wait_time = self.request_times[0] - minute_ago
                await asyncio.sleep(wait_time + 0.1)
                now = time.time()
                minute_ago = now - 60
                self.request_times = [t for t in self.request_times if t > minute_ago]

            # Check token limit
            current_tokens = sum(c for _, c in self.token_counts)
            while current_tokens + estimated_tokens > self.tokens_per_minute:
                if self.token_counts:
                    wait_time = self.token_counts[0][0] - minute_ago
                    await asyncio.sleep(wait_time + 0.1)
                    now = time.time()
                    minute_ago = now - 60
                    self.token_counts = [(t, c) for t, c in self.token_counts if t > minute_ago]
                    current_tokens = sum(c for _, c in self.token_counts)
                else:
                    break

            self.request_times.append(now)

    def record_tokens(self, tokens: int) -> None:
        """Record tokens used."""
        self.token_counts.append((time.time(), tokens))


class ClaudeClient:
    """
    Claude API client with streaming, tool use, and fallback support.

    Features:
    - Streaming responses
    - Tool use (function calling)
    - Multi-turn conversation
    - Rate limiting
    - Retry logic
    - Fallback to Ollama
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 8192,
        temperature: float = 0.7,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 100000,
        enable_ollama_fallback: bool = True,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.2",
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.enable_ollama_fallback = enable_ollama_fallback
        self.ollama_base_url = ollama_base_url
        self.ollama_model = ollama_model

        self._client: Optional[anthropic.AsyncAnthropic] = None
        self._rate_limiter = RateLimiter(requests_per_minute, tokens_per_minute)
        self._tools: Dict[str, ToolDefinition] = {}

    def _get_client(self) -> anthropic.AsyncAnthropic:
        """Get or create the Anthropic client."""
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool for use in conversations."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def _format_tools(self) -> List[Dict[str, Any]]:
        """Format tools for Claude API."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def _format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Format messages for Claude API."""
        formatted = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                continue  # System message handled separately

            content = []

            # Add text content
            if msg.content:
                content.append({"type": "text", "text": msg.content})

            # Add tool results
            if msg.tool_results:
                for result in msg.tool_results:
                    content.append({
                        "type": "tool_result",
                        "tool_use_id": result["tool_use_id"],
                        "content": result["content"],
                        "is_error": result.get("is_error", False),
                    })

            # Add tool calls (for assistant messages)
            if msg.tool_calls:
                for call in msg.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call["input"],
                    })

            formatted.append({
                "role": msg.role.value,
                "content": content if len(content) > 1 or (content and content[0].get("type") != "text") else msg.content,
            })

        return formatted

    def _get_system_message(self, messages: List[Message]) -> Optional[str]:
        """Extract system message from messages."""
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                return msg.content
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
    )
    async def complete(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        use_tools: bool = True,
    ) -> CompletionResponse:
        """
        Get a completion from Claude.

        Args:
            messages: Conversation messages
            system: System prompt (overrides message-based system prompt)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stop_sequences: Stop sequences
            use_tools: Whether to enable tool use

        Returns:
            CompletionResponse
        """
        await self._rate_limiter.acquire()
        start_time = time.time()

        try:
            client = self._get_client()

            # Build request
            request_params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature if temperature is not None else self.temperature,
                "messages": self._format_messages(messages),
            }

            # Add system message
            sys_msg = system or self._get_system_message(messages)
            if sys_msg:
                request_params["system"] = sys_msg

            # Add tools
            if use_tools and self._tools:
                request_params["tools"] = self._format_tools()

            # Add stop sequences
            if stop_sequences:
                request_params["stop_sequences"] = stop_sequences

            # Make request
            response = await client.messages.create(**request_params)

            # Record token usage
            self._rate_limiter.record_tokens(
                response.usage.input_tokens + response.usage.output_tokens
            )

            # Extract content
            content_parts = []
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    content_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            return CompletionResponse(
                content="\n".join(content_parts),
                stop_reason=StopReason(response.stop_reason),
                tool_calls=tool_calls,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                model=response.model,
                latency_ms=(time.time() - start_time) * 1000,
            )

        except (anthropic.APIError, anthropic.AuthenticationError) as e:
            logger.error(f"Claude API error: {e}")
            if self.enable_ollama_fallback:
                return await self._ollama_fallback(messages, system, max_tokens)
            raise

    async def stream(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_tools: bool = True,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream a completion from Claude.

        Args:
            messages: Conversation messages
            system: System prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            use_tools: Whether to enable tool use

        Yields:
            StreamChunk objects
        """
        await self._rate_limiter.acquire()

        try:
            client = self._get_client()

            # Build request
            request_params = {
                "model": self.model,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature if temperature is not None else self.temperature,
                "messages": self._format_messages(messages),
            }

            # Add system message
            sys_msg = system or self._get_system_message(messages)
            if sys_msg:
                request_params["system"] = sys_msg

            # Add tools
            if use_tools and self._tools:
                request_params["tools"] = self._format_tools()

            # Stream response
            current_tool_use = None
            current_tool_input = ""

            async with client.messages.stream(**request_params) as stream:
                async for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            current_tool_use = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                            }
                            current_tool_input = ""

                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield StreamChunk(
                                type="text",
                                content=event.delta.text,
                            )
                        elif event.delta.type == "input_json_delta":
                            current_tool_input += event.delta.partial_json

                    elif event.type == "content_block_stop":
                        if current_tool_use:
                            try:
                                tool_input = json.loads(current_tool_input) if current_tool_input else {}
                            except json.JSONDecodeError:
                                tool_input = {}

                            yield StreamChunk(
                                type="tool_use",
                                tool_name=current_tool_use["name"],
                                tool_input=tool_input,
                                tool_use_id=current_tool_use["id"],
                            )
                            current_tool_use = None

                    elif event.type == "message_stop":
                        yield StreamChunk(type="stop")

        except (anthropic.APIError, anthropic.AuthenticationError) as e:
            logger.error(f"Claude streaming error: {e}")
            if self.enable_ollama_fallback:
                async for chunk in self._ollama_stream_fallback(messages, system, max_tokens):
                    yield chunk
            else:
                raise

    async def complete_with_tools(
        self,
        messages: List[Message],
        system: Optional[str] = None,
        max_iterations: int = 10,
    ) -> CompletionResponse:
        """
        Complete with automatic tool execution.

        Args:
            messages: Conversation messages
            system: System prompt
            max_iterations: Maximum tool use iterations

        Returns:
            Final CompletionResponse
        """
        current_messages = messages.copy()

        for i in range(max_iterations):
            response = await self.complete(
                messages=current_messages,
                system=system,
                use_tools=True,
            )

            # If no tool calls, return
            if response.stop_reason != StopReason.TOOL_USE or not response.tool_calls:
                return response

            # Execute tools
            tool_results = []
            for call in response.tool_calls:
                tool_name = call["name"]
                tool_input = call["input"]

                tool = self._tools.get(tool_name)
                if tool and tool.handler:
                    try:
                        result = await tool.handler(**tool_input)
                        tool_results.append(ToolResult(
                            tool_use_id=call["id"],
                            content=str(result),
                            is_error=False,
                        ))
                    except Exception as e:
                        tool_results.append(ToolResult(
                            tool_use_id=call["id"],
                            content=f"Error: {str(e)}",
                            is_error=True,
                        ))
                else:
                    tool_results.append(ToolResult(
                        tool_use_id=call["id"],
                        content=f"Unknown tool: {tool_name}",
                        is_error=True,
                    ))

            # Add assistant message with tool calls
            current_messages.append(Message(
                role=MessageRole.ASSISTANT,
                content=response.content,
                tool_calls=response.tool_calls,
            ))

            # Add tool results
            current_messages.append(Message(
                role=MessageRole.USER,
                content="",
                tool_results=[
                    {
                        "tool_use_id": r.tool_use_id,
                        "content": r.content,
                        "is_error": r.is_error,
                    }
                    for r in tool_results
                ],
            ))

        # Max iterations reached
        return await self.complete(
            messages=current_messages,
            system=system,
            use_tools=False,
        )

    async def _ollama_fallback(
        self,
        messages: List[Message],
        system: Optional[str],
        max_tokens: Optional[int],
    ) -> CompletionResponse:
        """Fallback to Ollama for completion."""
        logger.info("Falling back to Ollama")
        start_time = time.time()

        # Format messages for Ollama
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        for msg in messages:
            if msg.role != MessageRole.SYSTEM:
                ollama_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens or self.max_tokens,
                    },
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()

        return CompletionResponse(
            content=data["message"]["content"],
            stop_reason=StopReason.END_TURN,
            tool_calls=[],
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            model=self.ollama_model,
            latency_ms=(time.time() - start_time) * 1000,
        )

    async def _ollama_stream_fallback(
        self,
        messages: List[Message],
        system: Optional[str],
        max_tokens: Optional[int],
    ) -> AsyncGenerator[StreamChunk, None]:
        """Fallback to Ollama for streaming."""
        logger.info("Falling back to Ollama (streaming)")

        # Format messages for Ollama
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        for msg in messages:
            if msg.role != MessageRole.SYSTEM:
                ollama_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.ollama_base_url}/api/chat",
                json={
                    "model": self.ollama_model,
                    "messages": ollama_messages,
                    "stream": True,
                    "options": {
                        "num_predict": max_tokens or self.max_tokens,
                    },
                },
                timeout=120.0,
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield StreamChunk(
                                type="text",
                                content=data["message"]["content"],
                            )
                        if data.get("done"):
                            yield StreamChunk(type="stop")


# Singleton instance
_claude_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """Get or create the Claude client singleton."""
    global _claude_client
    if _claude_client is None:
        from .config import get_settings
        settings = get_settings()
        _claude_client = ClaudeClient(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
            temperature=settings.claude_temperature,
            requests_per_minute=settings.requests_per_minute,
            tokens_per_minute=settings.tokens_per_minute,
            enable_ollama_fallback=settings.enable_ollama_fallback,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
        )
    return _claude_client
