"""Tests for the learning service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os

from src.models import (
    Interaction,
    InteractionOutcome,
    Feedback,
    FeedbackType,
    Pattern,
    PatternCategory,
    LearningMetrics,
)
from src.database import LearningDatabase
from src.learner import PatternAnalyzer, Learner, get_learner


class TestModels:
    """Test data models."""

    def test_interaction_creation(self):
        """Test creating an interaction."""
        interaction = Interaction(
            id="test-1",
            user_id="user-1",
            timestamp=datetime.utcnow().isoformat(),
            input_text="Hello JARVIS",
            output_text="Hello, how can I help?",
        )

        assert interaction.id == "test-1"
        assert interaction.outcome == InteractionOutcome.UNKNOWN
        assert interaction.feedback is None

    def test_pattern_creation(self):
        """Test creating a pattern."""
        pattern = Pattern(
            id="pattern-1",
            category=PatternCategory.CONVERSATION_STYLE,
            description="User prefers concise responses",
            pattern_data={"style": "concise"},
            confidence=0.8,
            occurrences=5,
            last_seen=datetime.utcnow().isoformat(),
            first_seen=datetime.utcnow().isoformat(),
        )

        assert pattern.category == PatternCategory.CONVERSATION_STYLE
        assert pattern.confidence == 0.8

    def test_learning_metrics(self):
        """Test metrics calculations."""
        metrics = LearningMetrics(
            total_interactions=100,
            successful_interactions=80,
            failed_interactions=20,
            positive_feedback_count=30,
            negative_feedback_count=10,
            patterns_learned=5,
            avg_response_time_ms=500,
            success_rate=0.8,
            improvement_trend=0.1,
        )

        assert metrics.success_rate == 0.8
        assert metrics.improvement_trend > 0


class TestDatabase:
    """Test database operations."""

    @pytest.fixture
    async def db(self):
        """Create a test database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = LearningDatabase(db_path)
        await db.initialize()

        yield db

        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_store_interaction(self, db):
        """Test storing an interaction."""
        interaction = Interaction(
            id="test-1",
            user_id="user-1",
            timestamp=datetime.utcnow().isoformat(),
            input_text="Test input",
            output_text="Test output",
        )

        result = await db.store_interaction(interaction)
        assert result == "test-1"

        # Retrieve it
        retrieved = await db.get_interaction("test-1")
        assert retrieved is not None
        assert retrieved.input_text == "Test input"

    @pytest.mark.asyncio
    async def test_store_pattern(self, db):
        """Test storing a pattern."""
        pattern = Pattern(
            id="pattern-1",
            category=PatternCategory.USER_PREFERENCE,
            description="Test pattern",
            pattern_data={"key": "value"},
            confidence=0.7,
            occurrences=3,
            last_seen=datetime.utcnow().isoformat(),
            first_seen=datetime.utcnow().isoformat(),
        )

        result = await db.store_pattern(pattern)
        assert result == "pattern-1"

        # Retrieve patterns
        patterns = await db.get_patterns(category=PatternCategory.USER_PREFERENCE)
        assert len(patterns) == 1
        assert patterns[0].description == "Test pattern"

    @pytest.mark.asyncio
    async def test_store_feedback(self, db):
        """Test storing feedback."""
        # First store an interaction
        interaction = Interaction(
            id="test-1",
            user_id="user-1",
            timestamp=datetime.utcnow().isoformat(),
            input_text="Test",
            output_text="Response",
        )
        await db.store_interaction(interaction)

        # Store feedback
        feedback = Feedback(
            interaction_id="test-1",
            user_id="user-1",
            feedback_type=FeedbackType.POSITIVE,
            comment="Great response!",
            timestamp=datetime.utcnow().isoformat(),
        )

        result = await db.store_feedback(feedback)
        assert result is not None

        # Check interaction was updated
        retrieved = await db.get_interaction("test-1")
        assert retrieved.feedback == FeedbackType.POSITIVE

    @pytest.mark.asyncio
    async def test_get_metrics(self, db):
        """Test getting metrics."""
        # Store some interactions
        for i in range(10):
            interaction = Interaction(
                id=f"test-{i}",
                user_id="user-1",
                timestamp=datetime.utcnow().isoformat(),
                input_text=f"Test {i}",
                output_text=f"Response {i}",
                outcome=InteractionOutcome.SUCCESS if i < 8 else InteractionOutcome.FAILURE,
            )
            await db.store_interaction(interaction)

        # Get metrics
        metrics = await db.get_metrics(user_id="user-1")
        assert metrics.total_interactions == 10
        assert metrics.successful_interactions == 8
        assert metrics.failed_interactions == 2

    @pytest.mark.asyncio
    async def test_increment_pattern_occurrence(self, db):
        """Test incrementing pattern occurrences."""
        pattern = Pattern(
            id="pattern-1",
            category=PatternCategory.TASK_STRATEGY,
            description="Test",
            pattern_data={},
            occurrences=1,
            last_seen=datetime.utcnow().isoformat(),
            first_seen=datetime.utcnow().isoformat(),
        )
        await db.store_pattern(pattern)

        # Increment
        await db.increment_pattern_occurrence("pattern-1")

        # Check
        patterns = await db.get_patterns()
        assert patterns[0].occurrences == 2


class TestPatternAnalyzer:
    """Test pattern analyzer."""

    def test_extract_conversation_patterns(self):
        """Test extracting conversation style patterns."""
        analyzer = PatternAnalyzer()
        analyzer.min_occurrences = 2

        interactions = [
            Interaction(
                id=f"i-{i}",
                user_id="user-1",
                timestamp=datetime.utcnow().isoformat(),
                input_text="short" if i < 5 else "this is a longer message",
                output_text="response",
            )
            for i in range(10)
        ]

        patterns = analyzer.extract_conversation_patterns(interactions)
        assert len(patterns) >= 1

        # Should detect conversation style
        style_patterns = [p for p in patterns if p.category == PatternCategory.CONVERSATION_STYLE]
        assert len(style_patterns) > 0

    def test_extract_preference_patterns(self):
        """Test extracting user preference patterns."""
        analyzer = PatternAnalyzer()
        analyzer.min_occurrences = 2

        interactions = [
            Interaction(
                id=f"i-{i}",
                user_id="user-1",
                timestamp=datetime.utcnow().isoformat(),
                input_text="test",
                output_text="response",
                agent_used="python-expert",
                feedback=FeedbackType.POSITIVE if i < 3 else FeedbackType.NEGATIVE,
            )
            for i in range(5)
        ]

        patterns = analyzer.extract_preference_patterns(interactions)

        # Should detect agent preference
        pref_patterns = [p for p in patterns if p.category == PatternCategory.USER_PREFERENCE]
        assert len(pref_patterns) > 0

    def test_extract_error_patterns(self):
        """Test extracting error patterns."""
        analyzer = PatternAnalyzer()
        analyzer.min_occurrences = 2

        interactions = [
            Interaction(
                id=f"i-{i}",
                user_id="user-1",
                timestamp=datetime.utcnow().isoformat(),
                input_text="complex database query with joins",
                output_text="error",
                outcome=InteractionOutcome.FAILURE,
            )
            for i in range(5)
        ]

        patterns = analyzer.extract_error_patterns(interactions)

        # Should detect failure pattern
        error_patterns = [p for p in patterns if p.category == PatternCategory.FAILED_APPROACH]
        assert len(error_patterns) > 0


class TestLearner:
    """Test learner functionality."""

    @pytest.fixture
    def learner(self):
        """Create a learner with mock DB."""
        learner = get_learner("test-token")
        return learner

    @pytest.mark.asyncio
    async def test_record_interaction(self):
        """Test recording an interaction."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        with patch("src.learner.get_database") as mock_get_db:
            db = LearningDatabase(db_path)
            await db.initialize()
            mock_get_db.return_value = db

            learner = Learner("test-token")

            interaction = await learner.record_interaction(
                user_id="user-1",
                input_text="Hello",
                output_text="Hi there!",
                intent="greeting",
            )

            assert interaction.id is not None
            assert interaction.user_id == "user-1"

            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_get_applicable_patterns(self):
        """Test getting applicable patterns."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        with patch("src.learner.get_database") as mock_get_db:
            db = LearningDatabase(db_path)
            await db.initialize()
            mock_get_db.return_value = db

            # Store a pattern
            pattern = Pattern(
                id="pattern-1",
                category=PatternCategory.ERROR_RECOVERY,
                description="Fix for database error",
                pattern_data={
                    "original_input": "database query error",
                    "correction": "Use parameterized queries",
                },
                confidence=0.9,
                occurrences=5,
                last_seen=datetime.utcnow().isoformat(),
                first_seen=datetime.utcnow().isoformat(),
                user_specific=True,
                user_id="user-1",
            )
            await db.store_pattern(pattern)

            learner = Learner("test-token")

            # Get applicable patterns
            patterns = await learner.get_applicable_patterns(
                user_id="user-1",
                input_text="database query error",
            )

            # Should find the error recovery pattern
            assert len(patterns) > 0

            os.unlink(db_path)

    def test_text_similarity(self):
        """Test text similarity calculation."""
        learner = Learner("test-token")

        # Similar texts
        sim1 = learner._text_similarity("hello world", "hello world")
        assert sim1 == 1.0

        sim2 = learner._text_similarity("hello world", "hello there")
        assert 0 < sim2 < 1

        # Different texts
        sim3 = learner._text_similarity("hello", "goodbye")
        assert sim3 == 0


class TestGetLearner:
    """Test get_learner function."""

    def test_get_learner_caches(self):
        """Test that learners are cached by token."""
        learner1 = get_learner("token-1")
        learner2 = get_learner("token-1")
        learner3 = get_learner("token-2")

        assert learner1 is learner2
        assert learner1 is not learner3
