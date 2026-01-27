"""Main agent router coordinating classification, caching, and prompt composition."""

import logging
import os
from typing import Optional

from .models import (
    AgentDefinition,
    AgentSession,
    ClassificationResult,
    RoutingResult,
    AgentSummary,
    CategoryInfo,
)
from .registry import AgentRegistry, get_agent_registry
from .classifier import IntentClassifier, get_intent_classifier
from .session_cache import get_session_cache
from .prompt_composer import PromptComposer, get_prompt_composer

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Main router coordinating agent selection and prompt composition.

    Flow:
    1. Check session cache for existing agent
    2. If cached and topic unchanged, use cached agent
    3. Otherwise, classify intent and select agent
    4. Compose prompt with selected agent
    5. Update session cache
    """

    def __init__(
        self,
        registry: AgentRegistry,
        classifier: IntentClassifier,
        session_cache,
        prompt_composer: PromptComposer,
        topic_change_threshold: float = 0.7,
    ):
        self.registry = registry
        self.classifier = classifier
        self.session_cache = session_cache
        self.prompt_composer = prompt_composer
        self.topic_change_threshold = topic_change_threshold

    async def route(
        self,
        message: str,
        session_id: str,
        conversation_history: list[dict] = None,
        preferred_title: str = "sir",
        context: str = "",
        force_agent: Optional[str] = None,
    ) -> RoutingResult:
        """
        Route a message to the appropriate agent.

        Args:
            message: User's message
            session_id: Conversation session ID
            conversation_history: Recent conversation messages
            preferred_title: User's preferred title
            context: Additional context (weather, calendar, etc.)
            force_agent: Force specific agent (bypasses classification)

        Returns:
            RoutingResult with composed prompt and metadata
        """
        conversation_history = conversation_history or []

        # Handle forced agent
        if force_agent:
            agent = self.registry.get_agent(force_agent)
            if agent:
                return await self._create_routing_result(
                    agent=agent,
                    classification=ClassificationResult(
                        agent_id=force_agent,
                        confidence=1.0,
                        reasoning="Forced agent selection",
                        is_explicit_request=True,
                    ),
                    session_id=session_id,
                    preferred_title=preferred_title,
                    context=context,
                    cache_hit=False,
                    include_handoff=True,
                )

        # Check session cache
        cached_session = await self.session_cache.get_session(session_id)
        cached_agent_id = cached_session.current_agent_id if cached_session else None

        # Classify intent
        classification = await self.classifier.classify(message, conversation_history)

        # Decide whether to use cached agent or new classification
        use_cached = False
        if cached_agent_id and classification.agent_id:
            # Check if this is a topic change
            if cached_agent_id == classification.agent_id:
                use_cached = True
            elif classification.confidence < self.topic_change_threshold:
                # Low confidence in new agent - stick with cached
                use_cached = True
                logger.info(f"Sticking with cached agent {cached_agent_id} (low confidence in {classification.agent_id})")

        # Get the agent to use
        if use_cached and cached_agent_id:
            agent = self.registry.get_agent(cached_agent_id)
            if agent:
                await self.session_cache.increment_message_count(session_id)
                return await self._create_routing_result(
                    agent=agent,
                    classification=classification,
                    session_id=session_id,
                    preferred_title=preferred_title,
                    context=context,
                    cache_hit=True,
                    include_handoff=False,  # No handoff for continued conversation
                    message_count=cached_session.message_count + 1 if cached_session else 1,
                )

        # Use classified agent
        agent = None
        if classification.agent_id:
            agent = self.registry.get_agent(classification.agent_id)

        # Handle multi-domain requests
        if classification.is_multi_domain and classification.secondary_agents:
            return await self._handle_multi_domain(
                primary_agent=agent,
                secondary_agent_ids=classification.secondary_agents,
                classification=classification,
                session_id=session_id,
                preferred_title=preferred_title,
                context=context,
            )

        # Standard single-agent routing
        return await self._create_routing_result(
            agent=agent,
            classification=classification,
            session_id=session_id,
            preferred_title=preferred_title,
            context=context,
            cache_hit=False,
            include_handoff=agent is not None,
        )

    async def _create_routing_result(
        self,
        agent: Optional[AgentDefinition],
        classification: ClassificationResult,
        session_id: str,
        preferred_title: str,
        context: str,
        cache_hit: bool,
        include_handoff: bool,
        message_count: int = 1,
    ) -> RoutingResult:
        """Create a routing result with composed prompt."""

        # Add continuation context if this is an ongoing conversation with the agent
        full_context = context
        if agent and message_count > 1:
            continuation = self.prompt_composer.generate_continuation_context(agent, message_count)
            if continuation:
                full_context = f"{continuation}\n\n{context}" if context else continuation

        # Compose prompt
        composed_prompt, handoff_text = self.prompt_composer.compose_prompt(
            agent=agent,
            preferred_title=preferred_title,
            context=full_context,
            include_handoff=include_handoff,
        )

        # Update session cache
        if agent:
            await self.session_cache.update_agent(
                session_id=session_id,
                agent_id=agent.id,
                topic_context=classification.topic_summary,
            )
        elif classification.agent_id is None:
            # Clear agent from session when returning to default JARVIS
            await self.session_cache.update_agent(
                session_id=session_id,
                agent_id=None,
                topic_context="",
            )

        return RoutingResult(
            primary_agent=agent,
            secondary_agents=[],
            composed_prompt=composed_prompt,
            handoff_text=handoff_text if include_handoff else None,
            classification=classification,
            cache_hit=cache_hit,
            is_default_jarvis=agent is None,
        )

    async def _handle_multi_domain(
        self,
        primary_agent: Optional[AgentDefinition],
        secondary_agent_ids: list[str],
        classification: ClassificationResult,
        session_id: str,
        preferred_title: str,
        context: str,
    ) -> RoutingResult:
        """Handle multi-domain requests with sequential consultation."""

        if not primary_agent:
            # Fall back to default JARVIS
            return await self._create_routing_result(
                agent=None,
                classification=classification,
                session_id=session_id,
                preferred_title=preferred_title,
                context=context,
                cache_hit=False,
                include_handoff=False,
            )

        # Get secondary agents (limit to 3)
        secondary_agents = []
        for agent_id in secondary_agent_ids[:3]:
            agent = self.registry.get_agent(agent_id)
            if agent:
                secondary_agents.append(agent)

        if not secondary_agents:
            # No valid secondary agents, use single agent
            return await self._create_routing_result(
                agent=primary_agent,
                classification=classification,
                session_id=session_id,
                preferred_title=preferred_title,
                context=context,
                cache_hit=False,
                include_handoff=True,
            )

        # Compose multi-agent prompt
        composed_prompt, handoff_text = self.prompt_composer.compose_multi_agent_prompt(
            primary_agent=primary_agent,
            secondary_agents=secondary_agents,
            preferred_title=preferred_title,
            context=context,
        )

        # Update session with primary agent
        await self.session_cache.update_agent(
            session_id=session_id,
            agent_id=primary_agent.id,
            topic_context=classification.topic_summary,
        )

        return RoutingResult(
            primary_agent=primary_agent,
            secondary_agents=secondary_agents,
            composed_prompt=composed_prompt,
            handoff_text=handoff_text,
            classification=classification,
            cache_hit=False,
            is_default_jarvis=False,
        )

    # Convenience methods for agent information

    async def get_agent_info(self, agent_id: str) -> Optional[AgentDefinition]:
        """Get agent by ID."""
        return self.registry.get_agent(agent_id)

    async def list_agents(self, category: Optional[str] = None) -> list[AgentSummary]:
        """List all agents or filter by category."""
        if category:
            agents = self.registry.get_agents_by_category(category)
        else:
            agents = self.registry.get_all_agents()

        return [agent.to_summary() for agent in agents]

    async def search_agents(self, query: str) -> list[AgentSummary]:
        """Search agents by keyword."""
        agents = self.registry.search_by_keyword(query)
        return [agent.to_summary() for agent in agents]

    async def get_categories(self) -> list[CategoryInfo]:
        """Get all agent categories."""
        return self.registry.get_categories()

    async def reload_agents(self) -> tuple[int, list[str]]:
        """Reload agent definitions."""
        return self.registry.reload()


# Singleton
_router: AgentRouter | None = None


def get_agent_router(llm_client=None, redis_client=None) -> AgentRouter:
    """Get the agent router singleton."""
    global _router

    if _router is None:
        registry = get_agent_registry()

        # Initialize classifier (needs LLM client)
        classifier = get_intent_classifier(llm_client)

        # Initialize session cache
        session_cache = get_session_cache(redis_client)

        # Initialize prompt composer
        prompt_composer = get_prompt_composer()

        topic_threshold = float(os.environ.get("AGENT_TOPIC_CHANGE_THRESHOLD", "0.7"))

        _router = AgentRouter(
            registry=registry,
            classifier=classifier,
            session_cache=session_cache,
            prompt_composer=prompt_composer,
            topic_change_threshold=topic_threshold,
        )

    return _router
