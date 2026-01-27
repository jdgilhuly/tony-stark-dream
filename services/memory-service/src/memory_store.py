"""
Memory Store Module

Provides long-term memory storage and retrieval using ChromaDB.
Supports semantic search, importance scoring, and memory decay.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memories."""
    FACT = "fact"  # User stated a fact
    PREFERENCE = "preference"  # User preference
    INSTRUCTION = "instruction"  # User instruction/rule
    EVENT = "event"  # Past event
    ENTITY = "entity"  # Information about an entity
    TASK = "task"  # Completed task
    CONVERSATION = "conversation"  # Conversation summary


@dataclass
class Memory:
    """A memory record."""
    id: str
    user_id: str
    content: str
    memory_type: MemoryType
    importance: float  # 0-1 scale
    source_message_id: Optional[str]
    entities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    accessed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0


@dataclass
class MemorySearchResult:
    """A memory search result."""
    memory: Memory
    similarity: float
    relevance_score: float  # Combined similarity + importance + recency


class MemoryStore:
    """
    Vector-based memory store using ChromaDB.

    Features:
    - Semantic similarity search
    - Importance-based ranking
    - Memory decay over time
    - Entity-based retrieval
    """

    def __init__(
        self,
        persist_dir: str = "./data/chroma",
        collection_name: str = "jarvis_memories",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Initialize embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedder = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()

        logger.info(f"MemoryStore initialized with {self.collection.count()} memories")

    def _embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return self.embedder.encode(text, convert_to_numpy=True).tolist()

    def _calculate_relevance(
        self,
        similarity: float,
        importance: float,
        created_at: str,
        accessed_at: str,
        access_count: int,
    ) -> float:
        """
        Calculate relevance score combining multiple factors.

        Factors:
        - Semantic similarity (0-1)
        - Importance (0-1)
        - Recency (decay over time)
        - Access frequency
        """
        # Time decay (memories become less relevant over time)
        try:
            created = datetime.fromisoformat(created_at)
            days_old = (datetime.utcnow() - created).days
            recency_score = max(0, 1 - (days_old / 365))  # Decay over a year
        except Exception:
            recency_score = 0.5

        # Access frequency boost
        access_boost = min(1, access_count / 10) * 0.1

        # Combined score
        relevance = (
            similarity * 0.5 +
            importance * 0.3 +
            recency_score * 0.15 +
            access_boost * 0.05
        )

        return relevance

    async def store(self, memory: Memory) -> str:
        """
        Store a memory.

        Args:
            memory: Memory to store

        Returns:
            Memory ID
        """
        # Generate embedding
        embedding = self._embed(memory.content)

        # Prepare metadata
        metadata = {
            "user_id": memory.user_id,
            "memory_type": memory.memory_type.value,
            "importance": memory.importance,
            "source_message_id": memory.source_message_id or "",
            "entities": ",".join(memory.entities),
            "created_at": memory.created_at,
            "accessed_at": memory.accessed_at,
            "access_count": memory.access_count,
            **{f"meta_{k}": str(v) for k, v in memory.metadata.items()},
        }

        # Store in ChromaDB
        self.collection.add(
            ids=[memory.id],
            embeddings=[embedding],
            documents=[memory.content],
            metadatas=[metadata],
        )

        logger.info(f"Stored memory: {memory.id} ({memory.memory_type.value})")
        return memory.id

    async def search(
        self,
        query: str,
        user_id: str,
        memory_types: Optional[List[MemoryType]] = None,
        entities: Optional[List[str]] = None,
        min_importance: float = 0.0,
        max_results: int = 10,
    ) -> List[MemorySearchResult]:
        """
        Search memories by semantic similarity.

        Args:
            query: Search query
            user_id: User ID to filter by
            memory_types: Filter by memory types
            entities: Filter by entities
            min_importance: Minimum importance threshold
            max_results: Maximum results to return

        Returns:
            List of MemorySearchResult sorted by relevance
        """
        # Generate query embedding
        query_embedding = self._embed(query)

        # Build where clause
        where = {"user_id": user_id}
        if memory_types:
            where["memory_type"] = {"$in": [t.value for t in memory_types]}
        if min_importance > 0:
            where["importance"] = {"$gte": min_importance}

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            where=where,
            n_results=max_results * 2,  # Get extra for filtering
            include=["documents", "metadatas", "distances"],
        )

        # Process results
        search_results = []

        if results and results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                similarity = 1 - distance  # Convert distance to similarity

                # Filter by entities if specified
                if entities:
                    memory_entities = metadata.get("entities", "").split(",")
                    if not any(e in memory_entities for e in entities):
                        continue

                # Build memory object
                memory = Memory(
                    id=memory_id,
                    user_id=metadata["user_id"],
                    content=results["documents"][0][i],
                    memory_type=MemoryType(metadata["memory_type"]),
                    importance=metadata["importance"],
                    source_message_id=metadata.get("source_message_id") or None,
                    entities=metadata.get("entities", "").split(",") if metadata.get("entities") else [],
                    created_at=metadata.get("created_at", ""),
                    accessed_at=metadata.get("accessed_at", ""),
                    access_count=metadata.get("access_count", 0),
                )

                # Calculate relevance
                relevance = self._calculate_relevance(
                    similarity=similarity,
                    importance=memory.importance,
                    created_at=memory.created_at,
                    accessed_at=memory.accessed_at,
                    access_count=memory.access_count,
                )

                search_results.append(MemorySearchResult(
                    memory=memory,
                    similarity=similarity,
                    relevance_score=relevance,
                ))

        # Sort by relevance and limit
        search_results.sort(key=lambda x: x.relevance_score, reverse=True)
        search_results = search_results[:max_results]

        # Update access times for returned memories
        for result in search_results:
            await self._update_access(result.memory.id)

        return search_results

    async def get(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        results = self.collection.get(
            ids=[memory_id],
            include=["documents", "metadatas"],
        )

        if not results or not results["ids"]:
            return None

        metadata = results["metadatas"][0]
        return Memory(
            id=memory_id,
            user_id=metadata["user_id"],
            content=results["documents"][0],
            memory_type=MemoryType(metadata["memory_type"]),
            importance=metadata["importance"],
            source_message_id=metadata.get("source_message_id") or None,
            entities=metadata.get("entities", "").split(",") if metadata.get("entities") else [],
            created_at=metadata.get("created_at", ""),
            accessed_at=metadata.get("accessed_at", ""),
            access_count=metadata.get("access_count", 0),
        )

    async def update(self, memory_id: str, updates: Dict[str, Any]) -> bool:
        """Update a memory's metadata."""
        try:
            # Get current memory
            current = await self.get(memory_id)
            if not current:
                return False

            # Build updated metadata
            metadata = {
                "user_id": current.user_id,
                "memory_type": updates.get("memory_type", current.memory_type.value),
                "importance": updates.get("importance", current.importance),
                "source_message_id": current.source_message_id or "",
                "entities": ",".join(updates.get("entities", current.entities)),
                "created_at": current.created_at,
                "accessed_at": datetime.utcnow().isoformat(),
                "access_count": current.access_count,
            }

            # Update content if provided
            if "content" in updates:
                embedding = self._embed(updates["content"])
                self.collection.update(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[updates["content"]],
                    metadatas=[metadata],
                )
            else:
                self.collection.update(
                    ids=[memory_id],
                    metadatas=[metadata],
                )

            return True

        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        try:
            self.collection.delete(ids=[memory_id])
            logger.info(f"Deleted memory: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    async def _update_access(self, memory_id: str) -> None:
        """Update access time and count for a memory."""
        try:
            current = await self.get(memory_id)
            if current:
                self.collection.update(
                    ids=[memory_id],
                    metadatas=[{
                        "user_id": current.user_id,
                        "memory_type": current.memory_type.value,
                        "importance": current.importance,
                        "source_message_id": current.source_message_id or "",
                        "entities": ",".join(current.entities),
                        "created_at": current.created_at,
                        "accessed_at": datetime.utcnow().isoformat(),
                        "access_count": current.access_count + 1,
                    }],
                )
        except Exception as e:
            logger.warning(f"Failed to update access for {memory_id}: {e}")

    async def get_by_entity(
        self,
        entity: str,
        user_id: str,
        max_results: int = 10,
    ) -> List[Memory]:
        """Get memories related to a specific entity."""
        # Search for entity in content
        results = await self.search(
            query=entity,
            user_id=user_id,
            max_results=max_results * 2,
        )

        # Filter to those containing the entity
        filtered = []
        for result in results:
            if entity.lower() in result.memory.content.lower():
                filtered.append(result.memory)
            elif entity in result.memory.entities:
                filtered.append(result.memory)

        return filtered[:max_results]

    async def get_recent(
        self,
        user_id: str,
        days: int = 7,
        max_results: int = 20,
    ) -> List[Memory]:
        """Get recent memories."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        results = self.collection.get(
            where={
                "user_id": user_id,
                "created_at": {"$gte": cutoff},
            },
            include=["documents", "metadatas"],
        )

        memories = []
        if results and results["ids"]:
            for i, memory_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i]
                memories.append(Memory(
                    id=memory_id,
                    user_id=metadata["user_id"],
                    content=results["documents"][i],
                    memory_type=MemoryType(metadata["memory_type"]),
                    importance=metadata["importance"],
                    source_message_id=metadata.get("source_message_id") or None,
                    entities=metadata.get("entities", "").split(",") if metadata.get("entities") else [],
                    created_at=metadata.get("created_at", ""),
                    accessed_at=metadata.get("accessed_at", ""),
                    access_count=metadata.get("access_count", 0),
                ))

        # Sort by created_at descending
        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[:max_results]

    def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for a user."""
        results = self.collection.get(
            where={"user_id": user_id},
            include=["metadatas"],
        )

        if not results or not results["ids"]:
            return {
                "total_memories": 0,
                "by_type": {},
                "avg_importance": 0,
            }

        by_type = {}
        total_importance = 0

        for metadata in results["metadatas"]:
            memory_type = metadata.get("memory_type", "unknown")
            by_type[memory_type] = by_type.get(memory_type, 0) + 1
            total_importance += metadata.get("importance", 0)

        return {
            "total_memories": len(results["ids"]),
            "by_type": by_type,
            "avg_importance": total_importance / len(results["ids"]) if results["ids"] else 0,
        }


# Singleton instance
_memory_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get or create the memory store singleton."""
    global _memory_store
    if _memory_store is None:
        from .config import get_settings
        settings = get_settings()
        _memory_store = MemoryStore(
            persist_dir=settings.chroma_persist_dir,
            collection_name=settings.chroma_collection_name,
            embedding_model=settings.embedding_model,
        )
    return _memory_store
