"""
JARVIS Claude Service - Main FastAPI Application

Provides Claude API integration with tool use and streaming support.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .claude_client import (
    ClaudeClient,
    get_claude_client,
    Message,
    MessageRole,
    CompletionResponse,
    StreamChunk,
)
from .tools import get_all_tools

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

    # Initialize Claude client and register tools
    client = get_claude_client()
    for tool in get_all_tools():
        client.register_tool(tool)

    yield
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Claude Service",
    description="Claude API integration with tool use and streaming",
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
class MessageRequest(BaseModel):
    role: str  # user, assistant, system
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None


class CompletionRequest(BaseModel):
    messages: List[MessageRequest]
    system: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    use_tools: bool = True
    stream: bool = False


class ToolCallRequest(BaseModel):
    messages: List[MessageRequest]
    system: Optional[str] = None
    max_iterations: int = 10


class CompletionResponseModel(BaseModel):
    content: str
    stop_reason: str
    tool_calls: List[Dict[str, Any]]
    input_tokens: int
    output_tokens: int
    model: str
    latency_ms: float


class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any]


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


def convert_messages(message_requests: List[MessageRequest]) -> List[Message]:
    """Convert request messages to internal Message format."""
    messages = []
    for msg in message_requests:
        messages.append(Message(
            role=MessageRole(msg.role),
            content=msg.content,
            tool_calls=msg.tool_calls,
            tool_results=msg.tool_results,
        ))
    return messages


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    client = get_claude_client()
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "model": settings.claude_model,
        "tools_registered": len(client._tools),
    }


# Completion endpoints
@app.post("/completion", response_model=CompletionResponseModel)
async def create_completion(
    request: CompletionRequest,
    user: dict = Depends(get_current_user),
):
    """Create a completion from Claude."""
    if request.stream:
        raise HTTPException(
            status_code=400,
            detail="Use /completion/stream for streaming responses"
        )

    try:
        client = get_claude_client()
        messages = convert_messages(request.messages)

        response = await client.complete(
            messages=messages,
            system=request.system,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stop_sequences=request.stop_sequences,
            use_tools=request.use_tools,
        )

        return CompletionResponseModel(
            content=response.content,
            stop_reason=response.stop_reason.value,
            tool_calls=response.tool_calls,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
            latency_ms=response.latency_ms,
        )

    except Exception as e:
        logger.error(f"Completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/completion/stream")
async def create_completion_stream(
    request: CompletionRequest,
    user: dict = Depends(get_current_user),
):
    """Create a streaming completion from Claude."""

    async def generate():
        try:
            client = get_claude_client()
            messages = convert_messages(request.messages)

            async for chunk in client.stream(
                messages=messages,
                system=request.system,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                use_tools=request.use_tools,
            ):
                if chunk.type == "text":
                    yield f"data: {{'type': 'text', 'content': {repr(chunk.content)}}}\n\n"
                elif chunk.type == "tool_use":
                    import json
                    yield f"data: {{'type': 'tool_use', 'name': '{chunk.tool_name}', 'id': '{chunk.tool_use_id}', 'input': {json.dumps(chunk.tool_input)}}}\n\n"
                elif chunk.type == "stop":
                    yield f"data: {{'type': 'stop'}}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {{'type': 'error', 'message': {repr(str(e))}}}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.post("/completion/tools", response_model=CompletionResponseModel)
async def create_completion_with_tools(
    request: ToolCallRequest,
    user: dict = Depends(get_current_user),
):
    """Create a completion with automatic tool execution."""
    try:
        client = get_claude_client()
        messages = convert_messages(request.messages)

        response = await client.complete_with_tools(
            messages=messages,
            system=request.system,
            max_iterations=request.max_iterations,
        )

        return CompletionResponseModel(
            content=response.content,
            stop_reason=response.stop_reason.value,
            tool_calls=response.tool_calls,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
            latency_ms=response.latency_ms,
        )

    except Exception as e:
        logger.error(f"Tool completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Tool management
@app.get("/tools", response_model=List[ToolInfo])
async def list_tools(user: dict = Depends(get_current_user)):
    """List all registered tools."""
    client = get_claude_client()
    return [
        ToolInfo(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
        )
        for tool in client._tools.values()
    ]


@app.get("/tools/{tool_name}", response_model=ToolInfo)
async def get_tool(tool_name: str, user: dict = Depends(get_current_user)):
    """Get information about a specific tool."""
    client = get_claude_client()
    tool = client._tools.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")

    return ToolInfo(
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema,
    )


# Convenience endpoints
@app.post("/ask")
async def ask(
    question: str,
    system: Optional[str] = None,
    use_tools: bool = True,
    user: dict = Depends(get_current_user),
):
    """
    Simple endpoint to ask Claude a question.
    """
    try:
        client = get_claude_client()
        messages = [Message(role=MessageRole.USER, content=question)]

        if use_tools:
            response = await client.complete_with_tools(
                messages=messages,
                system=system,
            )
        else:
            response = await client.complete(
                messages=messages,
                system=system,
                use_tools=False,
            )

        return {
            "answer": response.content,
            "model": response.model,
            "tokens": {
                "input": response.input_tokens,
                "output": response.output_tokens,
            },
        }

    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/code")
async def code_task(
    task: str,
    working_directory: str = ".",
    user: dict = Depends(get_current_user),
):
    """
    Execute a coding task like Claude Code.
    Automatically uses file, git, and execution tools.
    """
    system_prompt = f"""You are JARVIS, an expert AI coding assistant with access to tools for:
- Reading, writing, and editing files
- Searching code and finding files
- Running git commands
- Executing code

Working directory: {working_directory}

Analyze the task, use tools as needed, and provide clear explanations of what you did.
Be thorough and careful. Always verify your changes work."""

    try:
        client = get_claude_client()
        messages = [Message(role=MessageRole.USER, content=task)]

        response = await client.complete_with_tools(
            messages=messages,
            system=system_prompt,
            max_iterations=settings.max_tool_iterations,
        )

        return {
            "result": response.content,
            "tool_calls_made": len(response.tool_calls),
            "model": response.model,
            "tokens": {
                "input": response.input_tokens,
                "output": response.output_tokens,
            },
        }

    except Exception as e:
        logger.error(f"Code task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(
    messages: List[MessageRequest],
    system: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Multi-turn chat with Claude.
    """
    jarvis_system = system or """You are JARVIS (Just A Rather Very Intelligent System), a highly capable AI assistant.

You have access to various tools including:
- File operations (read, write, edit, search)
- Git operations
- Code execution
- Web browsing
- Memory/knowledge storage

Use these tools when helpful to accomplish tasks. Be helpful, precise, and efficient."""

    try:
        client = get_claude_client()
        converted_messages = convert_messages(messages)

        response = await client.complete_with_tools(
            messages=converted_messages,
            system=jarvis_system,
        )

        return {
            "response": response.content,
            "stop_reason": response.stop_reason.value,
            "tool_calls": response.tool_calls,
            "model": response.model,
            "tokens": {
                "input": response.input_tokens,
                "output": response.output_tokens,
            },
        }

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
