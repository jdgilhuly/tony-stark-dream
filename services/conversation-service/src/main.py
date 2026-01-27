import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Query
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
from .bedrock_client import get_bedrock_client, LLMClient, QuotaExceededError
from .memory import get_memory_manager, MemoryManager
from .integrations import get_integration_manager, IntegrationManager
from .agents import (
    AgentRouter,
    get_agent_router,
    get_agent_registry,
    get_session_cache,
    AgentSummary,
    CategoryInfo,
    AgentDetailResponse,
    AgentInfoResponse,
    ReloadResult,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Set agent definitions path
if not settings.agent_definitions_path:
    settings.agent_definitions_path = str(Path(__file__).parent.parent / "agents")
    os.environ["AGENT_DEFINITIONS_PATH"] = settings.agent_definitions_path

# Set agent configuration environment variables
os.environ["AGENT_CONFIDENCE_THRESHOLD"] = str(settings.agent_confidence_threshold)
os.environ["AGENT_SESSION_TTL_SECONDS"] = str(settings.agent_session_ttl_seconds)
os.environ["AGENT_TOPIC_CHANGE_THRESHOLD"] = str(settings.agent_topic_change_threshold)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {settings.service_name}")
    memory = get_memory_manager()
    await memory.connect()

    # Initialize agent registry
    if settings.agent_routing_enabled:
        registry = get_agent_registry()
        agent_count = len(registry.get_all_agents())
        category_count = len(registry.get_categories())
        logger.info(f"Agent routing enabled: {agent_count} agents in {category_count} categories")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}")
    await memory.disconnect()


app = FastAPI(
    title="JARVIS Conversation Service",
    description="Core conversation orchestration with local Ollama LLM and intelligent agent routing",
    version="0.3.0",
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


def get_agent_router_dep(
    bedrock: LLMClient = Depends(get_bedrock_client),
) -> AgentRouter:
    """Get agent router with dependencies."""
    if not settings.agent_routing_enabled:
        return None
    return get_agent_router(llm_client=bedrock, redis_client=None)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    registry = get_agent_registry() if settings.agent_routing_enabled else None
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "agent_routing_enabled": settings.agent_routing_enabled,
        "agents_loaded": len(registry.get_all_agents()) if registry else 0,
    }


@app.post("/conversation/message", response_model=ConversationResponse)
async def send_message(
    request: ConversationRequest,
    force_agent: Optional[str] = Query(None, description="Force specific agent by ID"),
    include_agent_info: bool = Query(False, description="Include agent routing metadata"),
    user: UserContext = Depends(get_current_user),
    memory: MemoryManager = Depends(get_memory_manager),
    bedrock: LLMClient = Depends(get_bedrock_client),
    integrations: IntegrationManager = Depends(get_integration_manager),
    router: AgentRouter = Depends(get_agent_router_dep),
):
    """Process a conversation message and generate response."""
    start_time = time.time()

    # Get authorization token from the original request for service-to-service calls
    auth_token = None

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

    # Prepare conversation history for routing
    conversation_history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in conversation.messages[-10:]  # Last 10 messages
    ]

    # Agent routing
    agent_info = None
    handoff_prefix = ""

    if settings.agent_routing_enabled and router:
        try:
            routing_result = await router.route(
                message=request.message,
                session_id=conversation_id,
                conversation_history=conversation_history,
                preferred_title=user.preferred_title,
                context=context,
                force_agent=force_agent,
            )

            # Use composed prompt from router
            system_prompt = routing_result.composed_prompt

            # Prepare handoff text if present
            if routing_result.handoff_text:
                handoff_prefix = routing_result.handoff_text + "\n\n"

            # Build agent info for response
            if include_agent_info or routing_result.primary_agent:
                agent_info = AgentInfoResponse(
                    agent_id=routing_result.primary_agent.id if routing_result.primary_agent else None,
                    agent_name=routing_result.primary_agent.name if routing_result.primary_agent else None,
                    confidence=routing_result.classification.confidence if routing_result.classification else None,
                    handoff_used=routing_result.handoff_text is not None,
                    is_default=routing_result.is_default_jarvis,
                )

            logger.info(
                f"Agent routing complete",
                extra={
                    "agent_id": routing_result.primary_agent.id if routing_result.primary_agent else "default",
                    "confidence": routing_result.classification.confidence if routing_result.classification else 0,
                    "cache_hit": routing_result.cache_hit,
                }
            )

        except Exception as e:
            logger.error(f"Agent routing failed, using default: {e}")
            # Fall back to default JARVIS prompt
            system_prompt = get_jarvis_prompt(
                preferred_title=user.preferred_title,
                context=context
            )
    else:
        # Agent routing disabled - use original prompt
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

        # Prepend handoff text if present
        if handoff_prefix:
            response_text = handoff_prefix + response_text

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
    message_metadata = {"usage": usage}
    if agent_info:
        message_metadata["agent"] = {
            "id": agent_info.agent_id,
            "name": agent_info.agent_name,
            "is_default": agent_info.is_default,
        }

    assistant_message = Message(
        id=str(uuid.uuid4()),
        role=MessageRole.ASSISTANT,
        content=response_text,
        timestamp=datetime.utcnow(),
        metadata=message_metadata
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
            "processing_time_ms": processing_time,
            "agent_used": agent_info.agent_id if agent_info else "default",
        }
    )

    return ConversationResponse(
        id=assistant_message.id,
        conversation_id=conversation_id,
        message=assistant_message,
        suggested_actions=[],
        processing_time_ms=processing_time
    )


# Agent API endpoints

@app.get("/agents", response_model=list[AgentSummary])
async def list_agents(
    category: Optional[str] = Query(None, description="Filter by category ID"),
    router: AgentRouter = Depends(get_agent_router_dep),
):
    """List all available agents or filter by category."""
    if not settings.agent_routing_enabled or not router:
        raise HTTPException(status_code=503, detail="Agent routing is disabled")

    return await router.list_agents(category)


@app.get("/agents/search", response_model=list[AgentSummary])
async def search_agents(
    q: str = Query(..., description="Search query"),
    router: AgentRouter = Depends(get_agent_router_dep),
):
    """Search agents by keyword."""
    if not settings.agent_routing_enabled or not router:
        raise HTTPException(status_code=503, detail="Agent routing is disabled")

    return await router.search_agents(q)


@app.get("/agents/categories", response_model=list[CategoryInfo])
async def list_categories(
    router: AgentRouter = Depends(get_agent_router_dep),
):
    """List all agent categories."""
    if not settings.agent_routing_enabled or not router:
        raise HTTPException(status_code=503, detail="Agent routing is disabled")

    return await router.get_categories()


@app.get("/agents/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    agent_id: str,
    router: AgentRouter = Depends(get_agent_router_dep),
):
    """Get detailed information about a specific agent."""
    if not settings.agent_routing_enabled or not router:
        raise HTTPException(status_code=503, detail="Agent routing is disabled")

    agent = await router.get_agent_info(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    return AgentDetailResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        category=agent.category,
        category_name=agent.category_name,
        tools=agent.tools,
        expertise_areas=agent.expertise_areas,
        keywords=agent.keywords,
    )


@app.post("/agents/reload", response_model=ReloadResult)
async def reload_agents(
    router: AgentRouter = Depends(get_agent_router_dep),
):
    """Reload agent definitions from filesystem."""
    if not settings.agent_routing_enabled or not router:
        raise HTTPException(status_code=503, detail="Agent routing is disabled")

    count, errors = await router.reload_agents()
    categories = await router.get_categories()

    return ReloadResult(
        success=len(errors) == 0,
        agents_loaded=count,
        categories_loaded=len(categories),
        errors=errors,
    )


# Existing conversation endpoints

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
