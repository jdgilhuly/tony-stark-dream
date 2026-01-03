"""Memory management for conversation context."""

import json
import logging
from datetime import datetime
from typing import Optional
import redis.asyncio as redis

from .config import get_settings
from .models import Message, Conversation, MessageRole

logger = logging.getLogger(__name__)
settings = get_settings()


class MemoryManager:
    """
    Three-tier memory system:
    - Short-term: Redis (last 10-20 exchanges, 24hr TTL)
    - Working memory: PostgreSQL (last 7 days, summarized)
    - Long-term: Vector DB for semantic search (future implementation)
    """

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """Initialize Redis connection."""
        if not self._connected:
            self.redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self._connected = True
            logger.info("Memory manager connected to Redis")

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self._connected = False

    def _conversation_key(self, conversation_id: str) -> str:
        return f"conversation:{conversation_id}"

    def _user_conversations_key(self, user_id: str) -> str:
        return f"user:{user_id}:conversations"

    def _short_term_key(self, conversation_id: str) -> str:
        return f"short_term:{conversation_id}"

    async def store_conversation(self, conversation: Conversation) -> None:
        """Store conversation in Redis."""
        if not self.redis:
            await self.connect()

        key = self._conversation_key(conversation.id)
        data = conversation.model_dump_json()

        await self.redis.set(key, data, ex=settings.redis_ttl_working)

        # Track conversation for user
        user_key = self._user_conversations_key(conversation.user_id)
        await self.redis.sadd(user_key, conversation.id)
        await self.redis.expire(user_key, settings.redis_ttl_working)

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve conversation from Redis."""
        if not self.redis:
            await self.connect()

        key = self._conversation_key(conversation_id)
        data = await self.redis.get(key)

        if data:
            return Conversation.model_validate_json(data)
        return None

    async def add_message(self, conversation_id: str, message: Message) -> None:
        """Add a message to conversation."""
        conversation = await self.get_conversation(conversation_id)

        if conversation:
            conversation.messages.append(message)
            conversation.last_message_at = datetime.utcnow()
            await self.store_conversation(conversation)

            # Update short-term memory
            await self._update_short_term(conversation_id, conversation.messages)

    async def _update_short_term(
        self,
        conversation_id: str,
        messages: list[Message]
    ) -> None:
        """Keep only recent messages in short-term memory."""
        key = self._short_term_key(conversation_id)

        # Keep last N messages for context
        recent = messages[-settings.max_context_messages:]
        data = json.dumps([m.model_dump() for m in recent], default=str)

        await self.redis.set(key, data, ex=settings.redis_ttl_short)

    async def get_context_messages(
        self,
        conversation_id: str,
        max_messages: int = None
    ) -> list[Message]:
        """Get recent messages for LLM context."""
        if not self.redis:
            await self.connect()

        max_messages = max_messages or settings.max_context_messages
        key = self._short_term_key(conversation_id)

        data = await self.redis.get(key)
        if data:
            messages_data = json.loads(data)
            messages = [Message.model_validate(m) for m in messages_data]
            return messages[-max_messages:]

        # Fallback to full conversation
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            return conversation.messages[-max_messages:]

        return []

    async def get_user_conversations(self, user_id: str) -> list[str]:
        """Get all conversation IDs for a user."""
        if not self.redis:
            await self.connect()

        key = self._user_conversations_key(user_id)
        return list(await self.redis.smembers(key))

    async def delete_conversation(self, conversation_id: str, user_id: str) -> None:
        """Delete a conversation."""
        if not self.redis:
            await self.connect()

        # Delete conversation data
        await self.redis.delete(self._conversation_key(conversation_id))
        await self.redis.delete(self._short_term_key(conversation_id))

        # Remove from user's list
        user_key = self._user_conversations_key(user_id)
        await self.redis.srem(user_key, conversation_id)


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
