"""
JARVIS Memory Service - Main FastAPI Application

Provides long-term memory storage and semantic search.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .memory_store import (
    MemoryStore, Memory, MemoryType, MemorySearchResult,
    get_memory_store,
)

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
    # Initialize memory store
    get_memory_store()
    yield
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Memory Service",
    description="Long-term memory storage and semantic search",
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
class StoreMemoryRequest(BaseModel):
    content: str
    memory_type: str = "fact"  # fact, preference, instruction, event, entity, task, conversation
    importance: float = 0.5
    source_message_id: Optional[str] = None
    entities: List[str] = []
    metadata: Dict[str, Any] = {}


class SearchMemoryRequest(BaseModel):
    query: str
    memory_types: Optional[List[str]] = None
    entities: Optional[List[str]] = None
    min_importance: float = 0.0
    max_results: int = 10


class UpdateMemoryRequest(BaseModel):
    content: Optional[str] = None
    memory_type: Optional[str] = None
    importance: Optional[float] = None
    entities: Optional[List[str]] = None


class MemoryResponse(BaseModel):
    id: str
    content: str
    memory_type: str
    importance: float
    source_message_id: Optional[str]
    entities: List[str]
    created_at: str
    accessed_at: str
    access_count: int


class SearchResultResponse(BaseModel):
    memory: MemoryResponse
    similarity: float
    relevance_score: float


class MemoryStatsResponse(BaseModel):
    total_memories: int
    by_type: Dict[str, int]
    avg_importance: float


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


def memory_to_response(memory: Memory) -> MemoryResponse:
    """Convert Memory to response model."""
    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        memory_type=memory.memory_type.value,
        importance=memory.importance,
        source_message_id=memory.source_message_id,
        entities=memory.entities,
        created_at=memory.created_at,
        accessed_at=memory.accessed_at,
        access_count=memory.access_count,
    )


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    store = get_memory_store()
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "embedding_model": settings.embedding_model,
    }


# Memory Endpoints
@app.post("/memory", response_model=MemoryResponse)
async def store_memory(
    request: StoreMemoryRequest,
    user: dict = Depends(get_current_user),
):
    """
    Store a new memory.

    Memory types:
    - fact: User stated a fact (e.g., "My birthday is January 15th")
    - preference: User preference (e.g., "I prefer dark mode")
    - instruction: User instruction (e.g., "Always use formal language")
    - event: Past event (e.g., "We discussed the project yesterday")
    - entity: Information about an entity (e.g., "John is my manager")
    - task: Completed task (e.g., "Fixed the login bug")
    - conversation: Conversation summary
    """
    try:
        # Parse memory type
        try:
            memory_type = MemoryType(request.memory_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid memory type: {request.memory_type}. "
                       f"Valid types: {[t.value for t in MemoryType]}"
            )

        # Create memory
        memory = Memory(
            id=str(uuid.uuid4()),
            user_id=user["user_id"],
            content=request.content,
            memory_type=memory_type,
            importance=max(0, min(1, request.importance)),
            source_message_id=request.source_message_id,
            entities=request.entities,
            metadata=request.metadata,
        )

        # Store
        store = get_memory_store()
        await store.store(memory)

        logger.info(f"Stored memory for user {user['user_id']}: {memory.id}")

        return memory_to_response(memory)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Store memory error: {e}")
        raise HTTPException(status_code=500, detail="Failed to store memory")


@app.post("/memory/search", response_model=List[SearchResultResponse])
async def search_memories(
    request: SearchMemoryRequest,
    user: dict = Depends(get_current_user),
):
    """Search memories by semantic similarity."""
    try:
        # Parse memory types
        memory_types = None
        if request.memory_types:
            memory_types = []
            for t in request.memory_types:
                try:
                    memory_types.append(MemoryType(t.lower()))
                except ValueError:
                    pass  # Skip invalid types

        store = get_memory_store()
        results = await store.search(
            query=request.query,
            user_id=user["user_id"],
            memory_types=memory_types,
            entities=request.entities,
            min_importance=request.min_importance,
            max_results=request.max_results,
        )

        return [
            SearchResultResponse(
                memory=memory_to_response(r.memory),
                similarity=r.similarity,
                relevance_score=r.relevance_score,
            )
            for r in results
        ]

    except Exception as e:
        logger.error(f"Search memory error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/memory/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a memory by ID."""
    store = get_memory_store()
    memory = await store.get(memory_id)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    if memory.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return memory_to_response(memory)


@app.put("/memory/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    request: UpdateMemoryRequest,
    user: dict = Depends(get_current_user),
):
    """Update a memory."""
    store = get_memory_store()

    # Check ownership
    memory = await store.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    if memory.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Build updates
    updates = {}
    if request.content is not None:
        updates["content"] = request.content
    if request.memory_type is not None:
        updates["memory_type"] = request.memory_type
    if request.importance is not None:
        updates["importance"] = max(0, min(1, request.importance))
    if request.entities is not None:
        updates["entities"] = request.entities

    success = await store.update(memory_id, updates)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update memory")

    # Return updated memory
    updated = await store.get(memory_id)
    return memory_to_response(updated)


@app.delete("/memory/{memory_id}")
async def delete_memory(
    memory_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a memory (forget)."""
    store = get_memory_store()

    # Check ownership
    memory = await store.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    if memory.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    success = await store.delete(memory_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete memory")

    return {"status": "deleted", "memory_id": memory_id}


@app.get("/memory/entity/{entity}", response_model=List[MemoryResponse])
async def get_memories_by_entity(
    entity: str,
    max_results: int = 10,
    user: dict = Depends(get_current_user),
):
    """Get memories related to a specific entity."""
    store = get_memory_store()
    memories = await store.get_by_entity(entity, user["user_id"], max_results)
    return [memory_to_response(m) for m in memories]


@app.get("/memory/recent", response_model=List[MemoryResponse])
async def get_recent_memories(
    days: int = 7,
    max_results: int = 20,
    user: dict = Depends(get_current_user),
):
    """Get recent memories."""
    store = get_memory_store()
    memories = await store.get_recent(user["user_id"], days, max_results)
    return [memory_to_response(m) for m in memories]


@app.get("/memory/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(user: dict = Depends(get_current_user)):
    """Get memory statistics."""
    store = get_memory_store()
    stats = store.get_stats(user["user_id"])
    return MemoryStatsResponse(**stats)


# Convenience endpoints for natural language commands
@app.post("/remember")
async def remember(
    content: str,
    user: dict = Depends(get_current_user),
):
    """
    Simple endpoint to remember something.
    Equivalent to "Remember that {content}"
    """
    request = StoreMemoryRequest(
        content=content,
        memory_type="fact",
        importance=0.6,
    )
    return await store_memory(request, user)


@app.post("/forget/{memory_id}")
async def forget(
    memory_id: str,
    user: dict = Depends(get_current_user),
):
    """
    Simple endpoint to forget something.
    Equivalent to "Forget about {memory_id}"
    """
    return await delete_memory(memory_id, user)


@app.post("/recall")
async def recall(
    query: str,
    user: dict = Depends(get_current_user),
):
    """
    Simple endpoint to recall information.
    Equivalent to "What do you remember about {query}"
    """
    request = SearchMemoryRequest(query=query, max_results=5)
    return await search_memories(request, user)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
