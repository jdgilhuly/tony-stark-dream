"""Data models for agent routing system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


@dataclass
class AgentDefinition:
    """Represents a parsed agent definition from markdown."""

    id: str  # e.g., "python-pro"
    name: str  # e.g., "Python Pro"
    description: str  # Short description from frontmatter
    category: str  # e.g., "02-language-specialists"
    category_name: str  # e.g., "Language Specialists"
    tools: list[str]  # e.g., ["Read", "Write", "Edit", "Bash"]
    expertise_areas: list[str]  # Extracted from content
    keywords: list[str]  # Auto-generated for search
    full_prompt: str  # Full markdown content (without frontmatter)
    file_path: str  # Source file location
    loaded_at: datetime = field(default_factory=datetime.utcnow)

    def to_summary(self) -> "AgentSummary":
        """Convert to summary representation."""
        return AgentSummary(
            id=self.id,
            name=self.name,
            description=self.description,
            category=self.category,
            category_name=self.category_name,
        )


@dataclass
class AgentSession:
    """Session state for agent routing."""

    session_id: str
    current_agent_id: Optional[str] = None
    topic_context: str = ""  # Brief topic description
    message_count: int = 0  # Messages with this agent
    agent_history: list[str] = field(default_factory=list)  # Previous agents
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage."""
        return {
            "session_id": self.session_id,
            "current_agent_id": self.current_agent_id,
            "topic_context": self.topic_context,
            "message_count": self.message_count,
            "agent_history": self.agent_history,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentSession":
        """Create from dictionary (Redis retrieval)."""
        return cls(
            session_id=data["session_id"],
            current_agent_id=data.get("current_agent_id"),
            topic_context=data.get("topic_context", ""),
            message_count=data.get("message_count", 0),
            agent_history=data.get("agent_history", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


@dataclass
class ClassificationResult:
    """Result of intent classification."""

    agent_id: Optional[str]  # Selected agent ID, None if no match
    confidence: float  # 0.0 - 1.0
    reasoning: str  # Why this agent was selected
    is_explicit_request: bool = False  # User explicitly asked for agent
    is_multi_domain: bool = False  # Request spans multiple domains
    secondary_agents: list[str] = field(default_factory=list)  # For multi-domain
    topic_summary: str = ""  # Brief topic description


@dataclass
class RoutingResult:
    """Complete routing result with composed prompt."""

    primary_agent: Optional[AgentDefinition]
    secondary_agents: list[AgentDefinition] = field(default_factory=list)
    composed_prompt: str = ""  # Ready-to-use prompt
    handoff_text: Optional[str] = None  # Introduction text
    classification: Optional[ClassificationResult] = None
    cache_hit: bool = False  # Was agent from cache?
    is_default_jarvis: bool = False  # Using default JARVIS (no agent)


# Pydantic models for API responses

class AgentSummary(BaseModel):
    """Summary representation of an agent for API responses."""

    id: str
    name: str
    description: str
    category: str
    category_name: str


class CategoryInfo(BaseModel):
    """Information about an agent category."""

    id: str  # e.g., "02-language-specialists"
    name: str  # e.g., "Language Specialists"
    description: str
    agent_count: int
    agent_ids: list[str] = Field(default_factory=list)


class AgentInfoResponse(BaseModel):
    """Agent information included in conversation response."""

    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    confidence: Optional[float] = None
    handoff_used: bool = False
    is_default: bool = True


class AgentDetailResponse(BaseModel):
    """Detailed agent response for API."""

    id: str
    name: str
    description: str
    category: str
    category_name: str
    tools: list[str]
    expertise_areas: list[str]
    keywords: list[str]


class ReloadResult(BaseModel):
    """Result of agent reload operation."""

    success: bool
    agents_loaded: int
    categories_loaded: int
    errors: list[str] = Field(default_factory=list)
