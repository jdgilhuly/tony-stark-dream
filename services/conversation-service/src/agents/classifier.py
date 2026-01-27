"""Intent classifier for agent routing using LLM."""

import json
import logging
import re
from typing import Optional

from .models import ClassificationResult, AgentSummary
from .registry import get_agent_registry

logger = logging.getLogger(__name__)

# Patterns for explicit agent requests
EXPLICIT_AGENT_PATTERNS = [
    r"(?:ask|consult|talk to|speak with|get|use)\s+(?:the|a|our)?\s*(\w+(?:\s+\w+)?)\s*(?:expert|specialist|pro|agent)?",
    r"(?:connect me with|bring in|let me talk to)\s+(?:the|a|our)?\s*(\w+(?:\s+\w+)?)\s*(?:expert|specialist|pro|agent)?",
    r"(?:i need|i want|can i get)\s+(?:the|a|our)?\s*(\w+(?:\s+\w+)?)\s*(?:expert|specialist|pro|agent|help)?",
    r"(?:switch to|change to)\s+(?:the|a)?\s*(\w+(?:\s+\w+)?)\s*(?:expert|specialist|pro|agent)?",
]

# Classification prompt template
CLASSIFICATION_PROMPT = """You are an intent classifier for an AI assistant. Your job is to determine which specialist agent should handle a user's request.

Available agents (by category):

{agent_list}

User message: "{message}"

Recent conversation context (last 3 messages):
{context}

Analyze the user's message and determine:
1. Which agent is best suited to handle this request
2. Your confidence level (0.0-1.0)
3. Whether this spans multiple domains
4. A brief topic summary

Respond in JSON format only:
{{
  "agent_id": "agent-id-here or null if no specific agent needed",
  "confidence": 0.85,
  "reasoning": "Brief explanation",
  "is_multi_domain": false,
  "secondary_agents": [],
  "topic_summary": "Brief topic description"
}}

Rules:
- Return null for agent_id if the request is general conversation, greetings, weather, calendar, or doesn't need specialist expertise
- Only suggest secondary_agents if the request clearly spans multiple technical domains
- Confidence should be lower (< 0.6) for ambiguous requests
- Match coding/technical questions to appropriate language or domain specialists
- Return null for simple questions that don't need expert knowledge"""


class IntentClassifier:
    """Classifies user intent to select appropriate agent."""

    def __init__(self, llm_client, confidence_threshold: float = 0.6):
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.registry = get_agent_registry()

    async def classify(
        self,
        message: str,
        conversation_history: list[dict] = None,
    ) -> ClassificationResult:
        """Classify user intent and select appropriate agent."""

        # First check for explicit agent requests
        explicit_result = self._check_explicit_request(message)
        if explicit_result:
            return explicit_result

        # Build agent list for prompt
        agent_list = self._build_agent_list()

        # Build context from recent messages
        context = self._build_context(conversation_history or [])

        # Create classification prompt
        prompt = CLASSIFICATION_PROMPT.format(
            agent_list=agent_list,
            message=message,
            context=context,
        )

        try:
            # Call LLM for classification
            response_text, _ = await self.llm_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a precise intent classifier. Respond only with valid JSON.",
                max_tokens=500,
            )

            # Parse response
            result = self._parse_classification_response(response_text)
            return result

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Return default (no agent) on error
            return ClassificationResult(
                agent_id=None,
                confidence=0.0,
                reasoning=f"Classification error: {str(e)}",
            )

    def _check_explicit_request(self, message: str) -> Optional[ClassificationResult]:
        """Check if user explicitly requested an agent."""
        message_lower = message.lower()

        for pattern in EXPLICIT_AGENT_PATTERNS:
            match = re.search(pattern, message_lower)
            if match:
                requested = match.group(1).strip()

                # Try to find matching agent
                agent = self._find_agent_by_name(requested)
                if agent:
                    return ClassificationResult(
                        agent_id=agent.id,
                        confidence=1.0,
                        reasoning=f"User explicitly requested {agent.name}",
                        is_explicit_request=True,
                        topic_summary=f"User requested {agent.name}",
                    )

        return None

    def _find_agent_by_name(self, name: str) -> Optional[any]:
        """Find agent by name or keyword."""
        name_lower = name.lower().replace(" ", "-")

        # Direct ID match
        agent = self.registry.get_agent(name_lower)
        if agent:
            return agent

        # Try common variations
        variations = [
            name_lower,
            f"{name_lower}-pro",
            f"{name_lower}-expert",
            f"{name_lower}-specialist",
            f"{name_lower}-engineer",
            f"{name_lower}-developer",
        ]

        for var in variations:
            agent = self.registry.get_agent(var)
            if agent:
                return agent

        # Keyword search
        agents = self.registry.search_by_keyword(name_lower)
        if agents:
            return agents[0]  # Return best match

        return None

    def _build_agent_list(self) -> str:
        """Build a formatted list of agents for the classification prompt."""
        lines = []
        categories = self.registry.get_categories()

        for category in categories:
            lines.append(f"\n## {category.name}")
            agents = self.registry.get_agents_by_category(category.id)
            for agent in agents[:15]:  # Limit per category to control prompt size
                lines.append(f"- {agent.id}: {agent.description[:100]}...")

        return "\n".join(lines)

    def _build_context(self, history: list[dict]) -> str:
        """Build context string from conversation history."""
        if not history:
            return "No previous context."

        # Take last 3 messages
        recent = history[-3:] if len(history) > 3 else history
        context_parts = []

        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]  # Truncate long messages
            context_parts.append(f"{role}: {content}")

        return "\n".join(context_parts)

    def _parse_classification_response(self, response: str) -> ClassificationResult:
        """Parse LLM classification response."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())

            agent_id = data.get("agent_id")
            confidence = float(data.get("confidence", 0.5))

            # Validate agent exists
            if agent_id and not self.registry.get_agent(agent_id):
                logger.warning(f"Classifier returned unknown agent: {agent_id}")
                agent_id = None
                confidence = 0.0

            # Apply confidence threshold
            if confidence < self.confidence_threshold:
                agent_id = None

            return ClassificationResult(
                agent_id=agent_id,
                confidence=confidence,
                reasoning=data.get("reasoning", ""),
                is_multi_domain=data.get("is_multi_domain", False),
                secondary_agents=data.get("secondary_agents", []),
                topic_summary=data.get("topic_summary", ""),
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse classification response: {e}")
            return ClassificationResult(
                agent_id=None,
                confidence=0.0,
                reasoning=f"Parse error: {str(e)}",
            )


# Singleton instance
_classifier: IntentClassifier | None = None


def get_intent_classifier(llm_client=None) -> IntentClassifier:
    """Get the intent classifier singleton."""
    global _classifier
    if _classifier is None:
        if llm_client is None:
            raise ValueError("LLM client required for first initialization")
        confidence_threshold = float(
            __import__("os").environ.get("AGENT_CONFIDENCE_THRESHOLD", "0.6")
        )
        _classifier = IntentClassifier(llm_client, confidence_threshold)
    return _classifier
