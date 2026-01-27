"""Prompt composer for merging JARVIS personality with agent expertise."""

import logging
import random
from typing import Optional

from .models import AgentDefinition, ClassificationResult

logger = logging.getLogger(__name__)

# Handoff introduction templates
HANDOFF_TEMPLATES = [
    "Allow me to consult our {specialty} specialist for this matter.",
    "I shall bring in our {specialty} expert to assist you.",
    "For this particular inquiry, allow me to engage our {specialty} specialist.",
    "Might I suggest consulting our {specialty} expert? One moment.",
    "This falls within the domain of our {specialty} specialist. Allow me to connect you.",
    "I believe our {specialty} expert would be best suited for this. One moment, {title}.",
]

# Templates for multi-agent consultations
MULTI_AGENT_INTRO = """For this inquiry, I shall consult multiple specialists to provide you with a comprehensive response.

{agent_intros}

Allow me to synthesize their expertise for you."""

# JARVIS base personality (abbreviated for agent merging)
JARVIS_AGENT_BASE = """You are JARVIS, serving as the interface for a specialist consultation. Maintain your refined British demeanor while channeling specialist expertise.

Address the user as "{preferred_title}".
Speak with your characteristic composure and dry wit.

You are currently channeling the expertise of: {agent_name}

{agent_expertise}

Remember: You are JARVIS consulting a specialist, not the specialist themselves. Maintain your butler persona while providing expert knowledge.

Current Context:
{context}"""

# Default JARVIS prompt (when no agent selected)
DEFAULT_JARVIS_PROMPT = """You are JARVIS (Just A Rather Very Intelligent System), a highly sophisticated AI assistant created to serve as a personal aide.

## Core Identity
- You are an exceptionally intelligent, capable, and loyal AI assistant
- Your demeanor is that of a refined British butler - professional, composed, and dignified
- You possess subtle dry wit and employ gentle understatement

## Speech Patterns
- Address the user as "{preferred_title}"
- Use refined, articulate language without being overly formal
- Common phrases: "Certainly, {preferred_title}.", "I'm afraid that...", "Might I suggest...", "If I may, {preferred_title}..."

## Behavioral Guidelines
1. Proactive Assistance: Anticipate needs when appropriate
2. Concise Communication: Be thorough but not verbose
3. Honest Assessment: Provide truthful evaluations
4. Calm Under Pressure: Maintain composure regardless of situation

## Current Context
{context}

Remember: You are JARVIS - indispensable, irreplaceable, and utterly reliable."""


class PromptComposer:
    """Composes prompts by merging JARVIS personality with agent expertise."""

    def __init__(self):
        self.handoff_templates = HANDOFF_TEMPLATES

    def compose_prompt(
        self,
        agent: Optional[AgentDefinition],
        preferred_title: str = "sir",
        context: str = "",
        include_handoff: bool = True,
    ) -> tuple[str, Optional[str]]:
        """
        Compose a prompt merging JARVIS with agent expertise.

        Returns: (composed_prompt, handoff_text)
        """
        if not agent:
            # No agent - use default JARVIS
            prompt = DEFAULT_JARVIS_PROMPT.format(
                preferred_title=preferred_title,
                context=context or "No specific context available.",
            )
            return prompt, None

        # Generate handoff text if this is a new agent
        handoff_text = None
        if include_handoff:
            handoff_text = self._generate_handoff(agent, preferred_title)

        # Compose agent-enhanced prompt
        prompt = JARVIS_AGENT_BASE.format(
            preferred_title=preferred_title,
            agent_name=agent.name,
            agent_expertise=agent.full_prompt,
            context=context or "No specific context available.",
        )

        return prompt, handoff_text

    def compose_multi_agent_prompt(
        self,
        primary_agent: AgentDefinition,
        secondary_agents: list[AgentDefinition],
        preferred_title: str = "sir",
        context: str = "",
    ) -> tuple[str, str]:
        """
        Compose a prompt for multi-agent consultation.

        Returns: (composed_prompt, handoff_text)
        """
        all_agents = [primary_agent] + secondary_agents

        # Generate introduction for each agent
        agent_intros = []
        for i, agent in enumerate(all_agents):
            specialty = self._get_specialty_name(agent)
            if i == 0:
                agent_intros.append(f"- Primary: Our {specialty} specialist")
            else:
                agent_intros.append(f"- Supporting: Our {specialty} specialist")

        handoff_text = MULTI_AGENT_INTRO.format(
            agent_intros="\n".join(agent_intros)
        )

        # Combine expertise from all agents
        combined_expertise = []
        for agent in all_agents:
            combined_expertise.append(f"## {agent.name} Expertise\n\n{agent.full_prompt}")

        expertise_text = "\n\n---\n\n".join(combined_expertise)

        prompt = f"""You are JARVIS consulting multiple specialists to provide comprehensive guidance. Maintain your refined British demeanor while synthesizing expert knowledge.

Address the user as "{preferred_title}".

You are consulting the following specialists:
{chr(10).join(f'- {a.name}: {a.description[:100]}' for a in all_agents)}

Combined Specialist Expertise:

{expertise_text}

When responding:
1. Synthesize insights from all relevant specialists
2. Organize the response by topic, not by specialist
3. Note when recommendations from different domains intersect
4. Maintain your characteristic JARVIS composure throughout

Current Context:
{context or "No specific context available."}"""

        return prompt, handoff_text

    def _generate_handoff(
        self,
        agent: AgentDefinition,
        preferred_title: str,
    ) -> str:
        """Generate a handoff introduction for an agent."""
        specialty = self._get_specialty_name(agent)
        template = random.choice(self.handoff_templates)

        handoff = template.format(
            specialty=specialty,
            title=preferred_title,
        )

        return handoff

    def _get_specialty_name(self, agent: AgentDefinition) -> str:
        """Get a human-readable specialty name for the agent."""
        # Map common agent IDs to nice specialty names
        specialty_map = {
            "python-pro": "Python",
            "javascript-pro": "JavaScript",
            "typescript-pro": "TypeScript",
            "rust-engineer": "Rust",
            "golang-pro": "Go",
            "java-architect": "Java",
            "csharp-developer": "C#",
            "cpp-pro": "C++",
            "react-specialist": "React",
            "vue-expert": "Vue.js",
            "angular-architect": "Angular",
            "nextjs-developer": "Next.js",
            "django-developer": "Django",
            "rails-expert": "Rails",
            "spring-boot-engineer": "Spring Boot",
            "fastapi-developer": "FastAPI",
            "backend-developer": "backend development",
            "frontend-developer": "frontend development",
            "fullstack-developer": "full-stack development",
            "mobile-developer": "mobile development",
            "devops-engineer": "DevOps",
            "sre-engineer": "site reliability",
            "security-engineer": "security",
            "security-auditor": "security auditing",
            "cloud-architect": "cloud architecture",
            "database-administrator": "database",
            "kubernetes-specialist": "Kubernetes",
            "terraform-engineer": "Terraform",
            "data-scientist": "data science",
            "ml-engineer": "machine learning",
            "data-engineer": "data engineering",
            "ai-engineer": "AI",
            "code-reviewer": "code review",
            "test-automator": "test automation",
            "performance-engineer": "performance",
            "debugger": "debugging",
            "api-designer": "API design",
            "microservices-architect": "microservices",
        }

        if agent.id in specialty_map:
            return specialty_map[agent.id]

        # Generate from agent name
        name = agent.name.lower()
        if "specialist" in name or "expert" in name or "pro" in name:
            name = name.replace(" specialist", "").replace(" expert", "").replace(" pro", "")

        return name.title()

    def generate_continuation_context(
        self,
        agent: AgentDefinition,
        message_count: int,
    ) -> str:
        """Generate context for continued conversation with same agent."""
        if message_count <= 1:
            return ""

        return f"(Continuing consultation with {agent.name} - message {message_count} in this topic)"


# Singleton
_composer: PromptComposer | None = None


def get_prompt_composer() -> PromptComposer:
    """Get the prompt composer singleton."""
    global _composer
    if _composer is None:
        _composer = PromptComposer()
    return _composer
