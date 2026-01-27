"""Database operations for the learning service."""

import aiosqlite
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import get_settings
from .models import (
    Interaction,
    InteractionOutcome,
    Pattern,
    PatternCategory,
    Feedback,
    FeedbackType,
    LearningMetrics,
    ReflectionReport,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class LearningDatabase:
    """Database manager for learning data."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize the database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    output_text TEXT NOT NULL,
                    intent TEXT,
                    agent_used TEXT,
                    outcome TEXT DEFAULT 'unknown',
                    feedback TEXT,
                    response_time_ms REAL DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    occurrences INTEGER DEFAULT 1,
                    last_seen TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    user_specific INTEGER DEFAULT 0,
                    user_id TEXT,
                    active INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    interaction_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    comment TEXT,
                    correction TEXT,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reflections (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    insights TEXT NOT NULL,
                    improvements TEXT NOT NULL,
                    patterns TEXT NOT NULL,
                    action_items TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
                CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp);
                CREATE INDEX IF NOT EXISTS idx_patterns_category ON patterns(category);
                CREATE INDEX IF NOT EXISTS idx_feedback_interaction ON feedback(interaction_id);
            """)
            await db.commit()

    # Interaction operations
    async def store_interaction(self, interaction: Interaction) -> str:
        """Store an interaction."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO interactions
                   (id, user_id, timestamp, input_text, output_text, intent,
                    agent_used, outcome, feedback, response_time_ms, tokens_used, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    interaction.id,
                    interaction.user_id,
                    interaction.timestamp,
                    interaction.input_text,
                    interaction.output_text,
                    interaction.intent,
                    interaction.agent_used,
                    interaction.outcome.value,
                    interaction.feedback.value if interaction.feedback else None,
                    interaction.response_time_ms,
                    interaction.tokens_used,
                    json.dumps(interaction.metadata),
                ),
            )
            await db.commit()
        return interaction.id

    async def get_interaction(self, interaction_id: str) -> Optional[Interaction]:
        """Get an interaction by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM interactions WHERE id = ?", (interaction_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_interaction(row)
        return None

    async def get_recent_interactions(
        self,
        user_id: Optional[str] = None,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[Interaction]:
        """Get recent interactions."""
        query = "SELECT * FROM interactions"
        params = []

        conditions = []
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if since:
            conditions.append("timestamp >= ?")
            params.append(since.isoformat())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_interaction(row) for row in rows]

    async def update_interaction_outcome(
        self, interaction_id: str, outcome: InteractionOutcome
    ):
        """Update interaction outcome."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE interactions SET outcome = ? WHERE id = ?",
                (outcome.value, interaction_id),
            )
            await db.commit()

    # Pattern operations
    async def store_pattern(self, pattern: Pattern) -> str:
        """Store a pattern."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO patterns
                   (id, category, description, pattern_data, confidence,
                    occurrences, last_seen, first_seen, user_specific, user_id, active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    pattern.id,
                    pattern.category.value,
                    pattern.description,
                    json.dumps(pattern.pattern_data),
                    pattern.confidence,
                    pattern.occurrences,
                    pattern.last_seen,
                    pattern.first_seen,
                    1 if pattern.user_specific else 0,
                    pattern.user_id,
                    1 if pattern.active else 0,
                ),
            )
            await db.commit()
        return pattern.id

    async def get_patterns(
        self,
        category: Optional[PatternCategory] = None,
        user_id: Optional[str] = None,
        active_only: bool = True,
        min_confidence: float = 0,
    ) -> List[Pattern]:
        """Get patterns matching criteria."""
        query = "SELECT * FROM patterns WHERE 1=1"
        params = []

        if active_only:
            query += " AND active = 1"
        if category:
            query += " AND category = ?"
            params.append(category.value)
        if user_id:
            query += " AND (user_specific = 0 OR user_id = ?)"
            params.append(user_id)
        if min_confidence > 0:
            query += " AND confidence >= ?"
            params.append(min_confidence)

        query += " ORDER BY confidence DESC, occurrences DESC"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_pattern(row) for row in rows]

    async def increment_pattern_occurrence(self, pattern_id: str):
        """Increment pattern occurrence count."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE patterns
                   SET occurrences = occurrences + 1, last_seen = ?
                   WHERE id = ?""",
                (now, pattern_id),
            )
            await db.commit()

    # Feedback operations
    async def store_feedback(self, feedback: Feedback) -> int:
        """Store feedback."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO feedback
                   (interaction_id, user_id, feedback_type, comment, correction, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    feedback.interaction_id,
                    feedback.user_id,
                    feedback.feedback_type.value,
                    feedback.comment,
                    feedback.correction,
                    feedback.timestamp,
                ),
            )
            await db.commit()

            # Update interaction feedback
            await db.execute(
                "UPDATE interactions SET feedback = ? WHERE id = ?",
                (feedback.feedback_type.value, feedback.interaction_id),
            )
            await db.commit()

            return cursor.lastrowid

    # Metrics operations
    async def get_metrics(
        self,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> LearningMetrics:
        """Calculate learning metrics."""
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Base query conditions
            user_condition = "AND user_id = ?" if user_id else ""
            params = [since.isoformat()]
            if user_id:
                params.append(user_id)

            # Total and outcome counts
            async with db.execute(
                f"""SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN outcome = 'failure' THEN 1 ELSE 0 END) as failed,
                    AVG(response_time_ms) as avg_response_time
                FROM interactions
                WHERE timestamp >= ? {user_condition}""",
                params,
            ) as cursor:
                row = await cursor.fetchone()
                total = row["total"] or 0
                successful = row["successful"] or 0
                failed = row["failed"] or 0
                avg_response_time = row["avg_response_time"] or 0

            # Feedback counts
            async with db.execute(
                f"""SELECT
                    SUM(CASE WHEN feedback = 'positive' THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN feedback = 'negative' THEN 1 ELSE 0 END) as negative
                FROM interactions
                WHERE timestamp >= ? {user_condition}""",
                params,
            ) as cursor:
                row = await cursor.fetchone()
                positive = row["positive"] or 0
                negative = row["negative"] or 0

            # Pattern count
            pattern_params = []
            if user_id:
                pattern_query = "SELECT COUNT(*) as count FROM patterns WHERE active = 1 AND (user_specific = 0 OR user_id = ?)"
                pattern_params = [user_id]
            else:
                pattern_query = "SELECT COUNT(*) as count FROM patterns WHERE active = 1"

            async with db.execute(pattern_query, pattern_params) as cursor:
                row = await cursor.fetchone()
                patterns_learned = row["count"] or 0

            # Calculate improvement trend
            mid_point = since + (datetime.utcnow() - since) / 2
            async with db.execute(
                f"""SELECT
                    SUM(CASE WHEN timestamp < ? THEN
                        CASE WHEN outcome = 'success' THEN 1 ELSE 0 END
                    ELSE 0 END) as early_success,
                    SUM(CASE WHEN timestamp < ? THEN 1 ELSE 0 END) as early_total,
                    SUM(CASE WHEN timestamp >= ? THEN
                        CASE WHEN outcome = 'success' THEN 1 ELSE 0 END
                    ELSE 0 END) as late_success,
                    SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as late_total
                FROM interactions
                WHERE timestamp >= ? {user_condition}""",
                [mid_point.isoformat()] * 4 + params,
            ) as cursor:
                row = await cursor.fetchone()
                early_success = row["early_success"] or 0
                early_total = row["early_total"] or 1
                late_success = row["late_success"] or 0
                late_total = row["late_total"] or 1

            early_rate = early_success / early_total if early_total > 0 else 0
            late_rate = late_success / late_total if late_total > 0 else 0
            improvement_trend = late_rate - early_rate

        return LearningMetrics(
            total_interactions=total,
            successful_interactions=successful,
            failed_interactions=failed,
            positive_feedback_count=positive,
            negative_feedback_count=negative,
            patterns_learned=patterns_learned,
            avg_response_time_ms=avg_response_time,
            success_rate=successful / total if total > 0 else 0,
            improvement_trend=improvement_trend,
        )

    # Reflection operations
    async def store_reflection(self, reflection: ReflectionReport) -> str:
        """Store a reflection report."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO reflections
                   (id, timestamp, period_start, period_end, metrics,
                    insights, improvements, patterns, action_items)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    reflection.id,
                    reflection.timestamp,
                    reflection.period_start,
                    reflection.period_end,
                    json.dumps(reflection.metrics.__dict__),
                    json.dumps(reflection.insights),
                    json.dumps(reflection.improvements_suggested),
                    json.dumps([p.__dict__ for p in reflection.patterns_identified]),
                    json.dumps(reflection.action_items),
                ),
            )
            await db.commit()
        return reflection.id

    async def get_latest_reflection(self) -> Optional[ReflectionReport]:
        """Get the most recent reflection."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM reflections ORDER BY timestamp DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_reflection(row)
        return None

    # Helper methods
    def _row_to_interaction(self, row) -> Interaction:
        return Interaction(
            id=row["id"],
            user_id=row["user_id"],
            timestamp=row["timestamp"],
            input_text=row["input_text"],
            output_text=row["output_text"],
            intent=row["intent"],
            agent_used=row["agent_used"],
            outcome=InteractionOutcome(row["outcome"]) if row["outcome"] else InteractionOutcome.UNKNOWN,
            feedback=FeedbackType(row["feedback"]) if row["feedback"] else None,
            response_time_ms=row["response_time_ms"],
            tokens_used=row["tokens_used"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _row_to_pattern(self, row) -> Pattern:
        return Pattern(
            id=row["id"],
            category=PatternCategory(row["category"]),
            description=row["description"],
            pattern_data=json.loads(row["pattern_data"]),
            confidence=row["confidence"],
            occurrences=row["occurrences"],
            last_seen=row["last_seen"],
            first_seen=row["first_seen"],
            user_specific=bool(row["user_specific"]),
            user_id=row["user_id"],
            active=bool(row["active"]),
        )

    def _row_to_reflection(self, row) -> ReflectionReport:
        metrics_dict = json.loads(row["metrics"])
        patterns_data = json.loads(row["patterns"])

        return ReflectionReport(
            id=row["id"],
            timestamp=row["timestamp"],
            period_start=row["period_start"],
            period_end=row["period_end"],
            metrics=LearningMetrics(**metrics_dict),
            insights=json.loads(row["insights"]),
            improvements_suggested=json.loads(row["improvements"]),
            patterns_identified=[Pattern(**p) for p in patterns_data],
            action_items=json.loads(row["action_items"]),
        )


# Singleton instance
_db: Optional[LearningDatabase] = None


async def get_database() -> LearningDatabase:
    """Get the database instance."""
    global _db
    if _db is None:
        _db = LearningDatabase()
        await _db.initialize()
    return _db
