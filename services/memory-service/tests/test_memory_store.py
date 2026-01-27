"""
Memory Store Tests
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta

from src.memory_store import MemoryStore, Memory, MemoryType


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)


@pytest.fixture
def memory_store(temp_dir):
    """Create a memory store for testing."""
    return MemoryStore(
        persist_dir=temp_dir,
        collection_name="test_memories",
        embedding_model="all-MiniLM-L6-v2",
    )


class TestMemoryStore:
    """Test memory store operations."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, memory_store):
        """Test storing and retrieving a memory."""
        memory = Memory(
            id="test-1",
            user_id="user-1",
            content="My favorite color is blue",
            memory_type=MemoryType.PREFERENCE,
            importance=0.8,
            source_message_id=None,
        )

        await memory_store.store(memory)
        retrieved = await memory_store.get("test-1")

        assert retrieved is not None
        assert retrieved.id == "test-1"
        assert retrieved.content == "My favorite color is blue"
        assert retrieved.memory_type == MemoryType.PREFERENCE

    @pytest.mark.asyncio
    async def test_search_by_similarity(self, memory_store):
        """Test semantic similarity search."""
        # Store some memories
        memories = [
            Memory(
                id="color-1",
                user_id="user-1",
                content="My favorite color is blue",
                memory_type=MemoryType.PREFERENCE,
                importance=0.8,
                source_message_id=None,
            ),
            Memory(
                id="food-1",
                user_id="user-1",
                content="I love eating pizza",
                memory_type=MemoryType.PREFERENCE,
                importance=0.7,
                source_message_id=None,
            ),
            Memory(
                id="color-2",
                user_id="user-1",
                content="I also like the color green",
                memory_type=MemoryType.PREFERENCE,
                importance=0.6,
                source_message_id=None,
            ),
        ]

        for m in memories:
            await memory_store.store(m)

        # Search for color-related memories
        results = await memory_store.search(
            query="What colors do you like?",
            user_id="user-1",
            max_results=5,
        )

        assert len(results) >= 2
        # Color memories should rank higher
        color_ids = {"color-1", "color-2"}
        top_results = {r.memory.id for r in results[:2]}
        assert len(color_ids & top_results) >= 1

    @pytest.mark.asyncio
    async def test_filter_by_memory_type(self, memory_store):
        """Test filtering by memory type."""
        await memory_store.store(Memory(
            id="pref-1",
            user_id="user-1",
            content="I prefer dark mode",
            memory_type=MemoryType.PREFERENCE,
            importance=0.7,
            source_message_id=None,
        ))
        await memory_store.store(Memory(
            id="fact-1",
            user_id="user-1",
            content="The sky is blue",
            memory_type=MemoryType.FACT,
            importance=0.5,
            source_message_id=None,
        ))

        # Search only preferences
        results = await memory_store.search(
            query="dark mode",
            user_id="user-1",
            memory_types=[MemoryType.PREFERENCE],
        )

        assert len(results) == 1
        assert results[0].memory.memory_type == MemoryType.PREFERENCE

    @pytest.mark.asyncio
    async def test_filter_by_importance(self, memory_store):
        """Test filtering by importance."""
        await memory_store.store(Memory(
            id="high-1",
            user_id="user-1",
            content="Very important information",
            memory_type=MemoryType.FACT,
            importance=0.9,
            source_message_id=None,
        ))
        await memory_store.store(Memory(
            id="low-1",
            user_id="user-1",
            content="Less important information",
            memory_type=MemoryType.FACT,
            importance=0.2,
            source_message_id=None,
        ))

        # Search with min importance
        results = await memory_store.search(
            query="information",
            user_id="user-1",
            min_importance=0.5,
        )

        assert len(results) == 1
        assert results[0].memory.id == "high-1"

    @pytest.mark.asyncio
    async def test_update_memory(self, memory_store):
        """Test updating a memory."""
        await memory_store.store(Memory(
            id="update-1",
            user_id="user-1",
            content="Original content",
            memory_type=MemoryType.FACT,
            importance=0.5,
            source_message_id=None,
        ))

        success = await memory_store.update("update-1", {
            "content": "Updated content",
            "importance": 0.8,
        })

        assert success is True

        updated = await memory_store.get("update-1")
        assert updated.content == "Updated content"
        assert updated.importance == 0.8

    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_store):
        """Test deleting a memory."""
        await memory_store.store(Memory(
            id="delete-1",
            user_id="user-1",
            content="To be deleted",
            memory_type=MemoryType.FACT,
            importance=0.5,
            source_message_id=None,
        ))

        success = await memory_store.delete("delete-1")
        assert success is True

        deleted = await memory_store.get("delete-1")
        assert deleted is None

    @pytest.mark.asyncio
    async def test_user_isolation(self, memory_store):
        """Test that users can only see their own memories."""
        await memory_store.store(Memory(
            id="user1-mem",
            user_id="user-1",
            content="User 1 memory",
            memory_type=MemoryType.FACT,
            importance=0.5,
            source_message_id=None,
        ))
        await memory_store.store(Memory(
            id="user2-mem",
            user_id="user-2",
            content="User 2 memory",
            memory_type=MemoryType.FACT,
            importance=0.5,
            source_message_id=None,
        ))

        # User 1 should only see their memory
        results = await memory_store.search(
            query="memory",
            user_id="user-1",
        )

        assert len(results) == 1
        assert results[0].memory.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_get_by_entity(self, memory_store):
        """Test getting memories by entity."""
        await memory_store.store(Memory(
            id="john-1",
            user_id="user-1",
            content="John is my manager",
            memory_type=MemoryType.ENTITY,
            importance=0.7,
            source_message_id=None,
            entities=["John"],
        ))
        await memory_store.store(Memory(
            id="jane-1",
            user_id="user-1",
            content="Jane is a developer",
            memory_type=MemoryType.ENTITY,
            importance=0.6,
            source_message_id=None,
            entities=["Jane"],
        ))

        memories = await memory_store.get_by_entity("John", "user-1")

        assert len(memories) >= 1
        assert any(m.id == "john-1" for m in memories)

    @pytest.mark.asyncio
    async def test_memory_stats(self, memory_store):
        """Test getting memory statistics."""
        await memory_store.store(Memory(
            id="stat-1",
            user_id="user-1",
            content="Fact 1",
            memory_type=MemoryType.FACT,
            importance=0.5,
            source_message_id=None,
        ))
        await memory_store.store(Memory(
            id="stat-2",
            user_id="user-1",
            content="Preference 1",
            memory_type=MemoryType.PREFERENCE,
            importance=0.7,
            source_message_id=None,
        ))

        stats = memory_store.get_stats("user-1")

        assert stats["total_memories"] == 2
        assert MemoryType.FACT.value in stats["by_type"]
        assert MemoryType.PREFERENCE.value in stats["by_type"]


class TestMemoryTypes:
    """Test memory type handling."""

    def test_all_memory_types(self):
        """Test that all memory types are valid."""
        expected_types = ["fact", "preference", "instruction", "event", "entity", "task", "conversation"]

        for t in expected_types:
            assert MemoryType(t) is not None


class TestRelevanceScoring:
    """Test relevance scoring algorithm."""

    @pytest.mark.asyncio
    async def test_importance_affects_ranking(self, memory_store):
        """Test that importance affects ranking."""
        # Store two similar memories with different importance
        await memory_store.store(Memory(
            id="low-imp",
            user_id="user-1",
            content="The weather is nice today",
            memory_type=MemoryType.FACT,
            importance=0.2,
            source_message_id=None,
        ))
        await memory_store.store(Memory(
            id="high-imp",
            user_id="user-1",
            content="The weather is beautiful today",
            memory_type=MemoryType.FACT,
            importance=0.9,
            source_message_id=None,
        ))

        results = await memory_store.search(
            query="weather",
            user_id="user-1",
        )

        # Higher importance should rank higher
        assert results[0].memory.id == "high-imp"
