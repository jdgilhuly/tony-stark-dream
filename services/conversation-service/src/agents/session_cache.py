"""Session cache for agent routing state."""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from .models import AgentSession

logger = logging.getLogger(__name__)


class AgentSessionCache:
    """Redis-backed cache for agent session state."""

    def __init__(self, redis_client, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl = ttl_seconds
        self.key_prefix = "agent_session:"

    def _get_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}{session_id}"

    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get agent session from cache."""
        try:
            key = self._get_key(session_id)
            data = await self.redis.get(key)

            if data:
                session_data = json.loads(data)
                return AgentSession.from_dict(session_data)

            return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def set_session(self, session: AgentSession) -> bool:
        """Store agent session in cache."""
        try:
            key = self._get_key(session.session_id)
            session.updated_at = datetime.utcnow()
            data = json.dumps(session.to_dict())

            await self.redis.setex(key, self.ttl, data)
            return True

        except Exception as e:
            logger.error(f"Failed to set session {session.session_id}: {e}")
            return False

    async def update_agent(
        self,
        session_id: str,
        agent_id: Optional[str],
        topic_context: str = "",
    ) -> Optional[AgentSession]:
        """Update the current agent for a session."""
        session = await self.get_session(session_id)

        if session is None:
            session = AgentSession(session_id=session_id)

        # Track agent history
        if session.current_agent_id and session.current_agent_id != agent_id:
            if session.current_agent_id not in session.agent_history:
                session.agent_history.append(session.current_agent_id)
            # Keep only last 10 agents in history
            session.agent_history = session.agent_history[-10:]

        session.current_agent_id = agent_id
        session.topic_context = topic_context
        session.message_count = 1 if agent_id != session.current_agent_id else session.message_count + 1

        await self.set_session(session)
        return session

    async def increment_message_count(self, session_id: str) -> int:
        """Increment message count for current agent."""
        session = await self.get_session(session_id)

        if session:
            session.message_count += 1
            await self.set_session(session)
            return session.message_count

        return 0

    async def clear_session(self, session_id: str) -> bool:
        """Clear agent session from cache."""
        try:
            key = self._get_key(session_id)
            await self.redis.delete(key)
            return True

        except Exception as e:
            logger.error(f"Failed to clear session {session_id}: {e}")
            return False

    async def get_current_agent(self, session_id: str) -> Optional[str]:
        """Get current agent ID for session."""
        session = await self.get_session(session_id)
        return session.current_agent_id if session else None


class InMemorySessionCache:
    """In-memory fallback when Redis is unavailable."""

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self.sessions: dict[str, AgentSession] = {}

    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get agent session from memory."""
        session = self.sessions.get(session_id)

        if session:
            # Check TTL
            age = (datetime.utcnow() - session.updated_at).total_seconds()
            if age > self.ttl:
                del self.sessions[session_id]
                return None

        return session

    async def set_session(self, session: AgentSession) -> bool:
        """Store agent session in memory."""
        session.updated_at = datetime.utcnow()
        self.sessions[session.session_id] = session
        return True

    async def update_agent(
        self,
        session_id: str,
        agent_id: Optional[str],
        topic_context: str = "",
    ) -> Optional[AgentSession]:
        """Update the current agent for a session."""
        session = await self.get_session(session_id)

        if session is None:
            session = AgentSession(session_id=session_id)

        if session.current_agent_id and session.current_agent_id != agent_id:
            if session.current_agent_id not in session.agent_history:
                session.agent_history.append(session.current_agent_id)
            session.agent_history = session.agent_history[-10:]

        session.current_agent_id = agent_id
        session.topic_context = topic_context
        session.message_count = 1 if agent_id != session.current_agent_id else session.message_count + 1

        await self.set_session(session)
        return session

    async def increment_message_count(self, session_id: str) -> int:
        """Increment message count for current agent."""
        session = await self.get_session(session_id)

        if session:
            session.message_count += 1
            await self.set_session(session)
            return session.message_count

        return 0

    async def clear_session(self, session_id: str) -> bool:
        """Clear agent session from memory."""
        if session_id in self.sessions:
            del self.sessions[session_id]
        return True

    async def get_current_agent(self, session_id: str) -> Optional[str]:
        """Get current agent ID for session."""
        session = await self.get_session(session_id)
        return session.current_agent_id if session else None


# Singleton instance
_session_cache = None


def get_session_cache(redis_client=None) -> AgentSessionCache | InMemorySessionCache:
    """Get the session cache singleton."""
    global _session_cache

    if _session_cache is None:
        ttl = int(os.environ.get("AGENT_SESSION_TTL_SECONDS", "3600"))

        if redis_client:
            _session_cache = AgentSessionCache(redis_client, ttl)
        else:
            logger.warning("Redis not available, using in-memory session cache")
            _session_cache = InMemorySessionCache(ttl)

    return _session_cache
