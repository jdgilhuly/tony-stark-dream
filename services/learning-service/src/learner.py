"""Core learning and pattern recognition system."""

import hashlib
import logging
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np

from .config import get_settings
from .database import get_database, LearningDatabase
from .models import (
    Feedback,
    FeedbackType,
    Interaction,
    InteractionOutcome,
    LearningMetrics,
    Pattern,
    PatternCategory,
    ReflectionReport,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class PatternAnalyzer:
    """Analyzes interactions to identify patterns."""

    def __init__(self):
        self.min_occurrences = settings.pattern_min_occurrences

    def extract_intent_pattern(self, interactions: List[Interaction]) -> Optional[Pattern]:
        """Extract patterns from user intents."""
        if len(interactions) < self.min_occurrences:
            return None

        # Count intents
        intent_counts = Counter(i.intent for i in interactions if i.intent)
        if not intent_counts:
            return None

        most_common_intent, count = intent_counts.most_common(1)[0]
        if count < self.min_occurrences:
            return None

        # Analyze success rate for this intent
        intent_interactions = [i for i in interactions if i.intent == most_common_intent]
        successful = sum(1 for i in intent_interactions if i.outcome == InteractionOutcome.SUCCESS)
        success_rate = successful / len(intent_interactions) if intent_interactions else 0

        return Pattern(
            id=f"intent-{hashlib.md5(most_common_intent.encode()).hexdigest()[:8]}",
            category=PatternCategory.TASK_STRATEGY if success_rate > 0.7 else PatternCategory.FAILED_APPROACH,
            description=f"Pattern for intent: {most_common_intent}",
            pattern_data={
                "intent": most_common_intent,
                "count": count,
                "success_rate": success_rate,
            },
            confidence=success_rate,
            occurrences=count,
            last_seen=datetime.utcnow().isoformat(),
            first_seen=interactions[-1].timestamp if interactions else datetime.utcnow().isoformat(),
        )

    def extract_conversation_patterns(
        self, interactions: List[Interaction]
    ) -> List[Pattern]:
        """Extract conversation style patterns."""
        patterns = []

        if len(interactions) < self.min_occurrences:
            return patterns

        # Analyze input lengths
        input_lengths = [len(i.input_text.split()) for i in interactions]
        avg_input_length = np.mean(input_lengths)
        std_input_length = np.std(input_lengths)

        # Determine preferred style
        if avg_input_length < 10:
            style = "concise"
        elif avg_input_length < 30:
            style = "moderate"
        else:
            style = "detailed"

        patterns.append(
            Pattern(
                id=f"conv-style-{style}",
                category=PatternCategory.CONVERSATION_STYLE,
                description=f"User prefers {style} inputs",
                pattern_data={
                    "style": style,
                    "avg_words": avg_input_length,
                    "std_words": std_input_length,
                },
                confidence=0.7 if std_input_length < avg_input_length else 0.5,
                occurrences=len(interactions),
                last_seen=datetime.utcnow().isoformat(),
                first_seen=interactions[-1].timestamp if interactions else datetime.utcnow().isoformat(),
            )
        )

        # Question patterns
        question_count = sum(1 for i in interactions if "?" in i.input_text)
        command_count = sum(1 for i in interactions if i.input_text.strip().endswith(".") or not "?" in i.input_text)

        if question_count > command_count * 1.5:
            patterns.append(
                Pattern(
                    id="conv-style-questions",
                    category=PatternCategory.CONVERSATION_STYLE,
                    description="User prefers asking questions",
                    pattern_data={
                        "question_ratio": question_count / len(interactions),
                    },
                    confidence=0.6,
                    occurrences=question_count,
                    last_seen=datetime.utcnow().isoformat(),
                    first_seen=interactions[-1].timestamp if interactions else datetime.utcnow().isoformat(),
                )
            )

        return patterns

    def extract_preference_patterns(
        self, interactions: List[Interaction]
    ) -> List[Pattern]:
        """Extract user preference patterns from feedback."""
        patterns = []

        # Group by agent and analyze feedback
        agent_feedback = defaultdict(lambda: {"positive": 0, "negative": 0, "total": 0})

        for i in interactions:
            if i.agent_used and i.feedback:
                agent_feedback[i.agent_used]["total"] += 1
                if i.feedback == FeedbackType.POSITIVE:
                    agent_feedback[i.agent_used]["positive"] += 1
                elif i.feedback == FeedbackType.NEGATIVE:
                    agent_feedback[i.agent_used]["negative"] += 1

        for agent, stats in agent_feedback.items():
            if stats["total"] >= self.min_occurrences:
                satisfaction = stats["positive"] / stats["total"] if stats["total"] > 0 else 0.5
                patterns.append(
                    Pattern(
                        id=f"pref-agent-{hashlib.md5(agent.encode()).hexdigest()[:8]}",
                        category=PatternCategory.USER_PREFERENCE,
                        description=f"User satisfaction with {agent} agent",
                        pattern_data={
                            "agent": agent,
                            "positive": stats["positive"],
                            "negative": stats["negative"],
                            "total": stats["total"],
                            "satisfaction": satisfaction,
                        },
                        confidence=satisfaction,
                        occurrences=stats["total"],
                        last_seen=datetime.utcnow().isoformat(),
                        first_seen=datetime.utcnow().isoformat(),
                        user_specific=True,
                    )
                )

        return patterns

    def extract_error_patterns(
        self, interactions: List[Interaction]
    ) -> List[Pattern]:
        """Extract patterns from failed interactions."""
        patterns = []

        failed = [i for i in interactions if i.outcome == InteractionOutcome.FAILURE]
        if len(failed) < self.min_occurrences:
            return patterns

        # Group failures by common words
        word_counts = Counter()
        for i in failed:
            words = re.findall(r'\b\w+\b', i.input_text.lower())
            word_counts.update(words)

        # Find common error triggers
        common_words = word_counts.most_common(5)
        error_triggers = [w for w, c in common_words if c >= self.min_occurrences and len(w) > 3]

        if error_triggers:
            patterns.append(
                Pattern(
                    id=f"error-triggers-{hashlib.md5(','.join(error_triggers).encode()).hexdigest()[:8]}",
                    category=PatternCategory.FAILED_APPROACH,
                    description="Common words in failed interactions",
                    pattern_data={
                        "trigger_words": error_triggers,
                        "failure_count": len(failed),
                    },
                    confidence=len(failed) / len(interactions) if interactions else 0,
                    occurrences=len(failed),
                    last_seen=datetime.utcnow().isoformat(),
                    first_seen=failed[-1].timestamp if failed else datetime.utcnow().isoformat(),
                )
            )

        return patterns


class SelfReflector:
    """Generates self-reflection reports and insights."""

    def __init__(self, db: LearningDatabase, auth_token: str):
        self.db = db
        self.auth_token = auth_token
        self.analyzer = PatternAnalyzer()

    async def generate_reflection(
        self,
        period_hours: int = 24,
        user_id: Optional[str] = None,
    ) -> ReflectionReport:
        """Generate a self-reflection report."""
        now = datetime.utcnow()
        period_start = now - timedelta(hours=period_hours)

        # Get metrics
        metrics = await self.db.get_metrics(user_id=user_id, since=period_start)

        # Get recent interactions
        interactions = await self.db.get_recent_interactions(
            user_id=user_id,
            limit=500,
            since=period_start,
        )

        # Extract patterns
        all_patterns = []
        all_patterns.extend(self.analyzer.extract_conversation_patterns(interactions))
        all_patterns.extend(self.analyzer.extract_preference_patterns(interactions))
        all_patterns.extend(self.analyzer.extract_error_patterns(interactions))

        intent_pattern = self.analyzer.extract_intent_pattern(interactions)
        if intent_pattern:
            all_patterns.append(intent_pattern)

        # Generate insights
        insights = self._generate_insights(metrics, interactions, all_patterns)

        # Generate improvement suggestions
        improvements = self._generate_improvements(metrics, interactions, all_patterns)

        # Generate action items
        action_items = self._generate_action_items(metrics, improvements)

        return ReflectionReport(
            id=str(uuid.uuid4()),
            timestamp=now.isoformat(),
            period_start=period_start.isoformat(),
            period_end=now.isoformat(),
            metrics=metrics,
            insights=insights,
            improvements_suggested=improvements,
            patterns_identified=all_patterns,
            action_items=action_items,
        )

    def _generate_insights(
        self,
        metrics: LearningMetrics,
        interactions: List[Interaction],
        patterns: List[Pattern],
    ) -> List[str]:
        """Generate insights from metrics and patterns."""
        insights = []

        # Success rate insight
        if metrics.success_rate > 0.8:
            insights.append(f"High success rate ({metrics.success_rate:.1%}) indicates effective responses.")
        elif metrics.success_rate < 0.5:
            insights.append(f"Low success rate ({metrics.success_rate:.1%}) suggests need for improvement.")

        # Improvement trend
        if metrics.improvement_trend > 0.1:
            insights.append("Performance is improving over time.")
        elif metrics.improvement_trend < -0.1:
            insights.append("Performance has declined recently. Review recent changes.")

        # Feedback insights
        if metrics.positive_feedback_count > metrics.negative_feedback_count * 2:
            insights.append("User feedback is predominantly positive.")
        elif metrics.negative_feedback_count > metrics.positive_feedback_count:
            insights.append("Negative feedback exceeds positive. Focus on quality improvement.")

        # Response time insight
        if metrics.avg_response_time_ms > 5000:
            insights.append(f"Average response time ({metrics.avg_response_time_ms:.0f}ms) is high. Consider optimization.")

        # Pattern-based insights
        for pattern in patterns:
            if pattern.category == PatternCategory.CONVERSATION_STYLE:
                style = pattern.pattern_data.get("style")
                if style:
                    insights.append(f"User prefers {style} communication style.")
            elif pattern.category == PatternCategory.FAILED_APPROACH:
                triggers = pattern.pattern_data.get("trigger_words", [])
                if triggers:
                    insights.append(f"Common failure triggers: {', '.join(triggers[:3])}")

        return insights[:10]  # Limit to top 10

    def _generate_improvements(
        self,
        metrics: LearningMetrics,
        interactions: List[Interaction],
        patterns: List[Pattern],
    ) -> List[str]:
        """Generate improvement suggestions."""
        improvements = []

        if metrics.success_rate < 0.7:
            improvements.append("Review failed interactions to identify common issues.")

        if metrics.avg_response_time_ms > 3000:
            improvements.append("Optimize response generation for faster replies.")

        if metrics.negative_feedback_count > 5:
            improvements.append("Analyze negative feedback to understand user expectations.")

        # Pattern-based improvements
        for pattern in patterns:
            if pattern.category == PatternCategory.FAILED_APPROACH and pattern.confidence > 0.3:
                improvements.append(f"Address failure pattern: {pattern.description}")
            elif pattern.category == PatternCategory.USER_PREFERENCE:
                satisfaction = pattern.pattern_data.get("satisfaction", 0.5)
                agent = pattern.pattern_data.get("agent")
                if satisfaction < 0.5 and agent:
                    improvements.append(f"Improve {agent} agent responses based on low satisfaction.")

        return improvements[:5]  # Limit to top 5

    def _generate_action_items(
        self,
        metrics: LearningMetrics,
        improvements: List[str],
    ) -> List[str]:
        """Generate actionable items."""
        actions = []

        if metrics.patterns_learned < 10:
            actions.append("Collect more interaction data to identify patterns.")

        for imp in improvements[:3]:
            actions.append(f"Action: {imp}")

        if metrics.improvement_trend < 0:
            actions.append("Schedule review of recent system changes.")

        return actions


class Learner:
    """Main learning system orchestrator."""

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.analyzer = PatternAnalyzer()
        self._db: Optional[LearningDatabase] = None
        self._reflector: Optional[SelfReflector] = None

    async def get_db(self) -> LearningDatabase:
        if self._db is None:
            self._db = await get_database()
        return self._db

    async def get_reflector(self) -> SelfReflector:
        if self._reflector is None:
            db = await self.get_db()
            self._reflector = SelfReflector(db, self.auth_token)
        return self._reflector

    async def record_interaction(
        self,
        user_id: str,
        input_text: str,
        output_text: str,
        intent: Optional[str] = None,
        agent_used: Optional[str] = None,
        outcome: InteractionOutcome = InteractionOutcome.UNKNOWN,
        response_time_ms: float = 0,
        tokens_used: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Interaction:
        """Record a new interaction."""
        db = await self.get_db()

        interaction = Interaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            timestamp=datetime.utcnow().isoformat(),
            input_text=input_text,
            output_text=output_text,
            intent=intent,
            agent_used=agent_used,
            outcome=outcome,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            metadata=metadata or {},
        )

        await db.store_interaction(interaction)
        logger.info(f"Recorded interaction {interaction.id}")

        # Trigger pattern analysis in background
        await self._analyze_and_learn(user_id)

        return interaction

    async def record_feedback(
        self,
        interaction_id: str,
        user_id: str,
        feedback_type: FeedbackType,
        comment: Optional[str] = None,
        correction: Optional[str] = None,
    ) -> None:
        """Record feedback for an interaction."""
        db = await self.get_db()

        feedback = Feedback(
            interaction_id=interaction_id,
            user_id=user_id,
            feedback_type=feedback_type,
            comment=comment,
            correction=correction,
            timestamp=datetime.utcnow().isoformat(),
        )

        await db.store_feedback(feedback)
        logger.info(f"Recorded {feedback_type.value} feedback for {interaction_id}")

        # Learn from correction if provided
        if correction:
            await self._learn_from_correction(interaction_id, correction)

    async def _analyze_and_learn(self, user_id: str) -> None:
        """Analyze recent interactions and learn patterns."""
        db = await self.get_db()

        # Get recent interactions
        interactions = await db.get_recent_interactions(
            user_id=user_id,
            limit=100,
            since=datetime.utcnow() - timedelta(days=7),
        )

        if len(interactions) < settings.pattern_min_occurrences:
            return

        # Extract and store patterns
        all_patterns = []
        all_patterns.extend(self.analyzer.extract_conversation_patterns(interactions))
        all_patterns.extend(self.analyzer.extract_preference_patterns(interactions))

        for pattern in all_patterns:
            if pattern.user_specific:
                pattern.user_id = user_id

            existing_patterns = await db.get_patterns(
                category=pattern.category,
                user_id=user_id if pattern.user_specific else None,
            )

            # Check if similar pattern exists
            similar = next(
                (p for p in existing_patterns if p.id == pattern.id),
                None,
            )

            if similar:
                await db.increment_pattern_occurrence(similar.id)
            else:
                await db.store_pattern(pattern)
                logger.info(f"Learned new pattern: {pattern.description}")

    async def _learn_from_correction(
        self, interaction_id: str, correction: str
    ) -> None:
        """Learn from a user correction."""
        db = await self.get_db()

        interaction = await db.get_interaction(interaction_id)
        if not interaction:
            return

        # Store as error recovery pattern
        pattern = Pattern(
            id=f"correction-{interaction_id[:8]}",
            category=PatternCategory.ERROR_RECOVERY,
            description=f"Correction for: {interaction.input_text[:50]}...",
            pattern_data={
                "original_input": interaction.input_text,
                "original_output": interaction.output_text,
                "correction": correction,
            },
            confidence=0.8,  # High confidence for explicit corrections
            occurrences=1,
            last_seen=datetime.utcnow().isoformat(),
            first_seen=datetime.utcnow().isoformat(),
            user_specific=True,
            user_id=interaction.user_id,
        )

        await db.store_pattern(pattern)
        logger.info(f"Learned from correction for {interaction_id}")

        # Store correction in memory service for future retrieval
        await self._store_in_memory(interaction.user_id, pattern)

    async def _store_in_memory(self, user_id: str, pattern: Pattern) -> None:
        """Store learned pattern in memory service."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.memory_service_url}/memory/store",
                    json={
                        "content": f"Learned pattern: {pattern.description}. Data: {pattern.pattern_data}",
                        "memory_type": "skill",
                        "importance": pattern.confidence,
                        "metadata": {
                            "pattern_id": pattern.id,
                            "category": pattern.category.value,
                        },
                    },
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
                if response.status_code == 200:
                    logger.info(f"Stored pattern {pattern.id} in memory")
        except Exception as e:
            logger.warning(f"Failed to store pattern in memory: {e}")

    async def get_applicable_patterns(
        self,
        user_id: str,
        input_text: str,
        intent: Optional[str] = None,
    ) -> List[Pattern]:
        """Get patterns applicable to the current interaction."""
        db = await self.get_db()

        patterns = await db.get_patterns(
            user_id=user_id,
            active_only=True,
            min_confidence=settings.feedback_threshold,
        )

        # Filter to relevant patterns
        relevant = []
        for p in patterns:
            if p.category == PatternCategory.CONVERSATION_STYLE:
                relevant.append(p)
            elif p.category == PatternCategory.USER_PREFERENCE:
                relevant.append(p)
            elif p.category == PatternCategory.TASK_STRATEGY:
                if intent and p.pattern_data.get("intent") == intent:
                    relevant.append(p)
            elif p.category == PatternCategory.ERROR_RECOVERY:
                # Check if input is similar to the original
                original = p.pattern_data.get("original_input", "")
                if self._text_similarity(input_text, original) > 0.7:
                    relevant.append(p)

        return relevant

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple word-based similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    async def get_metrics(
        self, user_id: Optional[str] = None
    ) -> LearningMetrics:
        """Get learning metrics."""
        db = await self.get_db()
        return await db.get_metrics(user_id=user_id)

    async def reflect(
        self,
        period_hours: int = 24,
        user_id: Optional[str] = None,
    ) -> ReflectionReport:
        """Generate a self-reflection report."""
        reflector = await self.get_reflector()
        report = await reflector.generate_reflection(period_hours, user_id)

        # Store the reflection
        db = await self.get_db()
        await db.store_reflection(report)

        return report


# Instance cache
_learners: Dict[str, Learner] = {}


def get_learner(auth_token: str) -> Learner:
    """Get or create a learner instance."""
    if auth_token not in _learners:
        _learners[auth_token] = Learner(auth_token)
    return _learners[auth_token]
