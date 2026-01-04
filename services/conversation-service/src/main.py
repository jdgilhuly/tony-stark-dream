import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError

from .config import get_settings
from .models import (
    ConversationRequest,
    ConversationResponse,
    Conversation,
    Message,
    MessageRole,
    UserContext,
)
from .prompts import get_jarvis_prompt
from .bedrock_client import get_bedrock_client, BedrockClient, QuotaExceededError
from .memory import get_memory_manager, MemoryManager
from .integrations import get_integration_manager, IntegrationManager

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
    # Startup
    logger.info(f"Starting {settings.service_name}")
    memory = get_memory_manager()
    await memory.connect()

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}")
    await memory.disconnect()


app = FastAPI(
    title="JARVIS Conversation Service",
    description="Core conversation orchestration with AWS Bedrock",
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


async def get_current_user(request: Request) -> UserContext:
    """Extract user from JWT token (disabled for development)."""
    # Auth disabled for development - return default user
    return UserContext(
        user_id="dev-user",
        preferred_title="sir",
        timezone="UTC"
    )

    # Original auth code (commented out):
    # auth_header = request.headers.get("Authorization")
    # if not auth_header or not auth_header.startswith("Bearer "):
    #     raise HTTPException(status_code=401, detail="Missing authorization token")
    # token = auth_header.split(" ")[1]
    # try:
    #     payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    #     return UserContext(
    #         user_id=payload.get("userId"),
    #         preferred_title=payload.get("preferredTitle", "sir"),
    #         timezone=payload.get("timezone", "UTC")
    #     )
    # except JWTError as e:
    #     logger.error(f"JWT decode error: {e}")
    #     raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/conversation/message", response_model=ConversationResponse)
async def send_message(
    request: ConversationRequest,
    user: UserContext = Depends(get_current_user),
    memory: MemoryManager = Depends(get_memory_manager),
    bedrock: BedrockClient = Depends(get_bedrock_client),
    integrations: IntegrationManager = Depends(get_integration_manager)
):
    """Process a conversation message and generate response."""
    start_time = time.time()

    # Get authorization token from the original request for service-to-service calls
    auth_token = None
    # Note: In production, use a service token or pass through the user token

    # Get or create conversation
    conversation_id = request.conversation_id or str(uuid.uuid4())
    conversation = await memory.get_conversation(conversation_id)

    if not conversation:
        conversation = Conversation(
            id=conversation_id,
            user_id=user.user_id,
            messages=[],
            started_at=datetime.utcnow()
        )

    # Add user message
    user_message = Message(
        id=str(uuid.uuid4()),
        role=MessageRole.USER,
        content=request.message,
        timestamp=datetime.utcnow()
    )
    conversation.messages.append(user_message)

    # Build context with real-time data from integrations
    context_parts = []
    if user.timezone:
        context_parts.append(f"Current time in user's timezone ({user.timezone}): {datetime.utcnow().isoformat()}")
    if user.location:
        context_parts.append(f"User's location: {user.location}")
    if request.context_hints:
        context_parts.extend(request.context_hints)

    # Enrich context with data from integrated services
    try:
        integration_context = await integrations.get_context_data(token=auth_token)

        if integration_context.get("weather"):
            weather = integration_context["weather"]
            weather_str = f"Current weather: {weather.get('condition', 'Unknown')}, {weather.get('temperature', 'N/A')}°"
            if weather.get("location"):
                weather_str += f" in {weather['location']}"
            context_parts.append(weather_str)

        if integration_context.get("calendar"):
            cal = integration_context["calendar"]
            context_parts.append(f"Calendar: {cal.get('event_count', 0)} events today")
            if cal.get("next_event"):
                next_evt = cal["next_event"]
                context_parts.append(f"Next event: {next_evt.get('title', 'Untitled')} at {next_evt.get('start_time', 'TBD')}")

        if integration_context.get("tasks"):
            tasks = integration_context["tasks"]
            context_parts.append(f"Tasks: {tasks.get('pending_count', 0)} pending, {tasks.get('high_priority', 0)} high priority")
    except Exception as e:
        logger.warning(f"Failed to get integration context: {e}")

    context = "\n".join(context_parts) if context_parts else ""

    # Generate system prompt
    system_prompt = get_jarvis_prompt(
        preferred_title=user.preferred_title,
        context=context
    )

    # Get context messages for LLM
    context_messages = await memory.get_context_messages(conversation_id)
    if not context_messages:
        context_messages = conversation.messages
    else:
        # Add the new user message if not already included
        if context_messages[-1].id != user_message.id:
            context_messages.append(user_message)

    # Generate response via Bedrock
    try:
        response_text, usage = await bedrock.generate_response(
            messages=context_messages,
            system_prompt=system_prompt
        )
    except QuotaExceededError as e:
        logger.error(f"LLM quota exceeded: {e}")
        response_text = "I'm terribly sorry, sir, but my neural pathways require additional resources. The API quota has been exceeded. Please check your billing settings at platform.openai.com to restore my full capabilities."
        usage = {}
    except Exception as e:
        logger.error(f"Bedrock generation error: {e}")
        # Fallback response
        response_text = "I'm afraid I'm experiencing a momentary difficulty, sir. Might I ask you to repeat that?"
        usage = {}

    # Create assistant message
    assistant_message = Message(
        id=str(uuid.uuid4()),
        role=MessageRole.ASSISTANT,
        content=response_text,
        timestamp=datetime.utcnow(),
        metadata={"usage": usage}
    )
    conversation.messages.append(assistant_message)
    conversation.last_message_at = datetime.utcnow()

    # Store updated conversation
    await memory.store_conversation(conversation)

    processing_time = int((time.time() - start_time) * 1000)

    logger.info(
        f"Message processed",
        extra={
            "conversation_id": conversation_id,
            "user_id": user.user_id,
            "processing_time_ms": processing_time
        }
    )

    return ConversationResponse(
        id=assistant_message.id,
        conversation_id=conversation_id,
        message=assistant_message,
        suggested_actions=[],
        processing_time_ms=processing_time
    )


@app.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: UserContext = Depends(get_current_user),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """Get a conversation by ID."""
    conversation = await memory.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {"success": True, "data": conversation}


@app.get("/conversations")
async def list_conversations(
    user: UserContext = Depends(get_current_user),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """List all conversations for the current user."""
    conversation_ids = await memory.get_user_conversations(user.user_id)

    conversations = []
    for cid in conversation_ids:
        conv = await memory.get_conversation(cid)
        if conv:
            conversations.append({
                "id": conv.id,
                "started_at": conv.started_at,
                "last_message_at": conv.last_message_at,
                "message_count": len(conv.messages),
                "preview": conv.messages[-1].content[:100] if conv.messages else ""
            })

    # Sort by last message
    conversations.sort(key=lambda x: x["last_message_at"], reverse=True)

    return {"success": True, "data": conversations}


@app.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: UserContext = Depends(get_current_user),
    memory: MemoryManager = Depends(get_memory_manager)
):
    """Delete a conversation."""
    conversation = await memory.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await memory.delete_conversation(conversation_id, user.user_id)

    return {"success": True, "message": "Conversation deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
