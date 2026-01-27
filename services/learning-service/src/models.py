"""Data models for the learning service."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InteractionOutcome(str, Enum):
    """Outcome of an interaction."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class FeedbackType(str, Enum):
    """Type of user feedback."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTION = "correction"


class PatternCategory(str, Enum):
    """Categories of learned patterns."""
    USER_PREFERENCE = "user_preference"
    SUCCESSFUL_APPROACH = "successful_approach"
    FAILED_APPROACH = "failed_approach"
    CONVERSATION_STYLE = "conversation_style"
    TASK_STRATEGY = "task_strategy"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class Interaction:
    """A single interaction with the user."""
    id: str
    user_id: str
    timestamp: str
    input_text: str
    output_text: str
    intent: Optional[str] = None
    agent_used: Optional[str] = None
    outcome: InteractionOutcome = InteractionOutcome.UNKNOWN
    feedback: Optional[FeedbackType] = None
    response_time_ms: float = 0
    tokens_used: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Pattern:
    """A learned pattern."""
    id: str
    category: PatternCategory
    description: str
    pattern_data: Dict[str, Any]
    confidence: float = 0.5
    occurrences: int = 1
    last_seen: str = ""
    first_seen: str = ""
    user_specific: bool = False
    user_id: Optional[str] = None
    active: bool = True


@dataclass
class LearningMetrics:
    """Metrics for learning progress."""
    total_interactions: int = 0
    successful_interactions: int = 0
    failed_interactions: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    patterns_learned: int = 0
    avg_response_time_ms: float = 0
    success_rate: float = 0
    improvement_trend: float = 0  # Positive = improving


@dataclass
class ReflectionReport:
    """Self-reflection report."""
    id: str
    timestamp: str
    period_start: str
    period_end: str
    metrics: LearningMetrics
    insights: List[str]
    improvements_suggested: List[str]
    patterns_identified: List[Pattern]
    action_items: List[str]


@dataclass
class Feedback:
    """User feedback on an interaction."""
    interaction_id: str
    user_id: str
    feedback_type: FeedbackType
    comment: Optional[str] = None
    correction: Optional[str] = None
    timestamp: str = ""
