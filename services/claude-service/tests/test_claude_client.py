"""
Claude Client Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.claude_client import (
    ClaudeClient,
    Message,
    MessageRole,
    ToolDefinition,
    ToolResult,
    CompletionResponse,
    StreamChunk,
    StopReason,
    RateLimiter,
)


@pytest.fixture
def claude_client():
    """Create a Claude client for testing."""
    return ClaudeClient(
        api_key="test-api-key",
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.7,
        enable_ollama_fallback=True,
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.2",
    )


class TestClaudeClient:
    """Test Claude client operations."""

    def test_initialization(self, claude_client):
        """Test client initialization."""
        assert claude_client.api_key == "test-api-key"
        assert claude_client.model == "claude-sonnet-4-20250514"
        assert claude_client.max_tokens == 4096
        assert claude_client.temperature == 0.7
        assert claude_client.enable_ollama_fallback is True

    def test_register_tool(self, claude_client):
        """Test tool registration."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                },
                "required": ["param"]
            },
            handler=AsyncMock(return_value="result"),
        )

        claude_client.register_tool(tool)

        assert "test_tool" in claude_client._tools
        assert claude_client._tools["test_tool"].description == "A test tool"

    def test_unregister_tool(self, claude_client):
        """Test tool unregistration."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
        )
        claude_client.register_tool(tool)

        result = claude_client.unregister_tool("test_tool")

        assert result is True
        assert "test_tool" not in claude_client._tools

    def test_unregister_nonexistent_tool(self, claude_client):
        """Test unregistering a tool that doesn't exist."""
        result = claude_client.unregister_tool("nonexistent")
        assert result is False

    def test_format_tools(self, claude_client):
        """Test tool formatting for API."""
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                }
            },
        )
        claude_client.register_tool(tool)

        formatted = claude_client._format_tools()

        assert len(formatted) == 1
        assert formatted[0]["name"] == "test_tool"
        assert formatted[0]["description"] == "A test tool"
        assert "input_schema" in formatted[0]


class TestMessageFormatting:
    """Test message formatting."""

    def test_format_simple_messages(self, claude_client):
        """Test formatting simple messages."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        ]

        formatted = claude_client._format_messages(messages)

        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"
        assert formatted[1]["role"] == "assistant"
        assert formatted[1]["content"] == "Hi there!"

    def test_format_system_message_excluded(self, claude_client):
        """Test that system messages are excluded from formatted messages."""
        messages = [
            Message(role=MessageRole.SYSTEM, content="System prompt"),
            Message(role=MessageRole.USER, content="Hello"),
        ]

        formatted = claude_client._format_messages(messages)

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"

    def test_get_system_message(self, claude_client):
        """Test extracting system message."""
        messages = [
            Message(role=MessageRole.SYSTEM, content="System prompt"),
            Message(role=MessageRole.USER, content="Hello"),
        ]

        system = claude_client._get_system_message(messages)

        assert system == "System prompt"


class TestCompletion:
    """Test completion operations."""

    @pytest.mark.asyncio
    async def test_complete_success(self, claude_client):
        """Test successful completion."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello!")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)
        mock_response.model = "claude-sonnet-4-20250514"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        claude_client._client = mock_client

        messages = [Message(role=MessageRole.USER, content="Hello")]
        response = await claude_client.complete(messages)

        assert response.content == "Hello!"
        assert response.stop_reason == StopReason.END_TURN
        assert response.input_tokens == 10
        assert response.output_tokens == 5

    @pytest.mark.asyncio
    async def test_complete_with_tool_calls(self, claude_client):
        """Test completion that returns tool calls."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(type="text", text="Let me check that."),
            MagicMock(
                type="tool_use",
                id="tool_1",
                name="read_file",
                input={"path": "/test.txt"}
            ),
        ]
        mock_response.stop_reason = "tool_use"
        mock_response.usage = MagicMock(input_tokens=20, output_tokens=15)
        mock_response.model = "claude-sonnet-4-20250514"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        claude_client._client = mock_client

        messages = [Message(role=MessageRole.USER, content="Read the file")]
        response = await claude_client.complete(messages)

        assert response.stop_reason == StopReason.TOOL_USE
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["name"] == "read_file"


class TestStreaming:
    """Test streaming operations."""

    @pytest.mark.asyncio
    async def test_stream_text(self, claude_client):
        """Test streaming text response."""
        # Create mock stream events
        mock_events = [
            MagicMock(type="content_block_start", content_block=MagicMock(type="text")),
            MagicMock(type="content_block_delta", delta=MagicMock(type="text_delta", text="Hello")),
            MagicMock(type="content_block_delta", delta=MagicMock(type="text_delta", text=" world")),
            MagicMock(type="message_stop"),
        ]

        # Create async iterator
        async def mock_stream():
            for event in mock_events:
                yield event

        mock_stream_context = MagicMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_stream())
        mock_stream_context.__aexit__ = AsyncMock()

        mock_client = MagicMock()
        mock_client.messages.stream = MagicMock(return_value=mock_stream_context)
        claude_client._client = mock_client

        messages = [Message(role=MessageRole.USER, content="Hello")]
        chunks = []
        async for chunk in claude_client.stream(messages):
            chunks.append(chunk)

        assert len(chunks) == 3  # 2 text chunks + 1 stop
        assert chunks[0].type == "text"
        assert chunks[0].content == "Hello"
        assert chunks[1].content == " world"
        assert chunks[2].type == "stop"


class TestToolExecution:
    """Test tool execution."""

    @pytest.mark.asyncio
    async def test_complete_with_tools(self, claude_client):
        """Test completion with automatic tool execution."""
        # Register a test tool
        async def test_handler(path: str) -> str:
            return f"Content of {path}"

        tool = ToolDefinition(
            name="read_file",
            description="Read a file",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            },
            handler=test_handler,
        )
        claude_client.register_tool(tool)

        # First call returns tool use
        first_response = MagicMock()
        first_response.content = [
            MagicMock(
                type="tool_use",
                id="tool_1",
                name="read_file",
                input={"path": "/test.txt"}
            ),
        ]
        first_response.stop_reason = "tool_use"
        first_response.usage = MagicMock(input_tokens=10, output_tokens=10)
        first_response.model = "claude-sonnet-4-20250514"

        # Second call returns final response
        second_response = MagicMock()
        second_response.content = [MagicMock(type="text", text="The file contains test content.")]
        second_response.stop_reason = "end_turn"
        second_response.usage = MagicMock(input_tokens=20, output_tokens=10)
        second_response.model = "claude-sonnet-4-20250514"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=[first_response, second_response])
        claude_client._client = mock_client

        messages = [Message(role=MessageRole.USER, content="Read the test file")]
        response = await claude_client.complete_with_tools(messages, max_iterations=2)

        assert response.content == "The file contains test content."
        assert response.stop_reason == StopReason.END_TURN


class TestRateLimiter:
    """Test rate limiter."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=100000,
        )
        assert limiter.requests_per_minute == 60
        assert limiter.tokens_per_minute == 100000

    @pytest.mark.asyncio
    async def test_acquire_under_limit(self):
        """Test acquiring under rate limit."""
        limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=100000,
        )

        # Should complete without waiting
        await limiter.acquire(1000)
        assert len(limiter.request_times) == 1

    def test_record_tokens(self):
        """Test recording token usage."""
        limiter = RateLimiter(
            requests_per_minute=60,
            tokens_per_minute=100000,
        )

        limiter.record_tokens(5000)
        assert len(limiter.token_counts) == 1


class TestOllamaFallback:
    """Test Ollama fallback functionality."""

    @pytest.mark.asyncio
    async def test_ollama_fallback(self, claude_client):
        """Test fallback to Ollama."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {"content": "Ollama response"},
                "prompt_eval_count": 10,
                "eval_count": 5,
            }

            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()

            mock_client_class.return_value = mock_client

            messages = [Message(role=MessageRole.USER, content="Hello")]
            response = await claude_client._ollama_fallback(messages, None, 1000)

            assert response.content == "Ollama response"
            assert response.model == "llama3.2"


class TestToolResults:
    """Test tool result handling."""

    def test_tool_result_creation(self):
        """Test creating a tool result."""
        result = ToolResult(
            tool_use_id="tool_1",
            content="File content here",
            is_error=False,
        )

        assert result.tool_use_id == "tool_1"
        assert result.content == "File content here"
        assert result.is_error is False

    def test_tool_result_error(self):
        """Test creating an error tool result."""
        result = ToolResult(
            tool_use_id="tool_1",
            content="Error: File not found",
            is_error=True,
        )

        assert result.is_error is True


class TestStreamChunk:
    """Test stream chunk handling."""

    def test_text_chunk(self):
        """Test text stream chunk."""
        chunk = StreamChunk(
            type="text",
            content="Hello world",
        )

        assert chunk.type == "text"
        assert chunk.content == "Hello world"

    def test_tool_use_chunk(self):
        """Test tool use stream chunk."""
        chunk = StreamChunk(
            type="tool_use",
            tool_name="read_file",
            tool_input={"path": "/test.txt"},
            tool_use_id="tool_1",
        )

        assert chunk.type == "tool_use"
        assert chunk.tool_name == "read_file"
        assert chunk.tool_input == {"path": "/test.txt"}

    def test_stop_chunk(self):
        """Test stop stream chunk."""
        chunk = StreamChunk(type="stop")

        assert chunk.type == "stop"
