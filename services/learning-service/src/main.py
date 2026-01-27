"""
JARVIS Learning Service - Main FastAPI Application

Tracks interactions, learns patterns, and enables self-improvement.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .database import get_database
from .models import (
    FeedbackType,
    InteractionOutcome,
    LearningMetrics,
    PatternCategory,
)
from .learner import get_learner, Learner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.service_name}")
    # Initialize database
    db = await get_database()
    yield
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Learning Service",
    description="Self-improvement and learning system",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class InteractionRequest(BaseModel):
    input_text: str
    output_text: str
    intent: Optional[str] = None
    agent_used: Optional[str] = None
    outcome: str = "unknown"
    response_time_ms: float = 0
    tokens_used: int = 0
    metadata: Dict[str, Any] = {}


class InteractionResponse(BaseModel):
    id: str
    user_id: str
    timestamp: str


class FeedbackRequest(BaseModel):
    interaction_id: str
    feedback_type: str  # positive, negative, neutral, correction
    comment: Optional[str] = None
    correction: Optional[str] = None


class PatternResponse(BaseModel):
    id: str
    category: str
    description: str
    confidence: float
    occurrences: int
    pattern_data: Dict[str, Any]


class MetricsResponse(BaseModel):
    total_interactions: int
    successful_interactions: int
    failed_interactions: int
    positive_feedback_count: int
    negative_feedback_count: int
    patterns_learned: int
    avg_response_time_ms: float
    success_rate: float
    improvement_trend: float


class ReflectionResponse(BaseModel):
    id: str
    timestamp: str
    period_start: str
    period_end: str
    metrics: MetricsResponse
    insights: List[str]
    improvements_suggested: List[str]
    action_items: List[str]
    patterns_count: int


# Auth dependency
async def get_current_user(request: Request) -> dict:
    """Extract user from JWT token."""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return {"user_id": payload.get("userId"), "token": token}
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


def get_learner_instance(user: dict = Depends(get_current_user)) -> Learner:
    """Get learner instance for user."""
    return get_learner(user["token"])


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Record interaction
@app.post("/interaction", response_model=InteractionResponse)
async def record_interaction(
    request: InteractionRequest,
    user: dict = Depends(get_current_user),
    learner: Learner = Depends(get_learner_instance),
):
    """Record a new interaction for learning."""
    try:
        outcome = InteractionOutcome(request.outcome)
    except ValueError:
        outcome = InteractionOutcome.UNKNOWN

    interaction = await learner.record_interaction(
        user_id=user["user_id"],
        input_text=request.input_text,
        output_text=request.output_text,
        intent=request.intent,
        agent_used=request.agent_used,
        outcome=outcome,
        response_time_ms=request.response_time_ms,
        tokens_used=request.tokens_used,
        metadata=request.metadata,
    )

    return InteractionResponse(
        id=interaction.id,
        user_id=interaction.user_id,
        timestamp=interaction.timestamp,
    )


# Record feedback
@app.post("/feedback")
async def record_feedback(
    request: FeedbackRequest,
    user: dict = Depends(get_current_user),
    learner: Learner = Depends(get_learner_instance),
):
    """Record feedback for an interaction."""
    try:
        feedback_type = FeedbackType(request.feedback_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid feedback type")

    await learner.record_feedback(
        interaction_id=request.interaction_id,
        user_id=user["user_id"],
        feedback_type=feedback_type,
        comment=request.comment,
        correction=request.correction,
    )

    return {"status": "recorded", "interaction_id": request.interaction_id}


# Get patterns
@app.get("/patterns", response_model=List[PatternResponse])
async def get_patterns(
    category: Optional[str] = None,
    min_confidence: float = 0,
    user: dict = Depends(get_current_user),
    learner: Learner = Depends(get_learner_instance),
):
    """Get learned patterns."""
    db = await learner.get_db()

    cat = None
    if category:
        try:
            cat = PatternCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category")

    patterns = await db.get_patterns(
        category=cat,
        user_id=user["user_id"],
        min_confidence=min_confidence,
    )

    return [
        PatternResponse(
            id=p.id,
            category=p.category.value,
            description=p.description,
            confidence=p.confidence,
            occurrences=p.occurrences,
            pattern_data=p.pattern_data,
        )
        for p in patterns
    ]


# Get applicable patterns for input
@app.post("/patterns/applicable", response_model=List[PatternResponse])
async def get_applicable_patterns(
    input_text: str,
    intent: Optional[str] = None,
    user: dict = Depends(get_current_user),
    learner: Learner = Depends(get_learner_instance),
):
    """Get patterns applicable to the given input."""
    patterns = await learner.get_applicable_patterns(
        user_id=user["user_id"],
        input_text=input_text,
        intent=intent,
    )

    return [
        PatternResponse(
            id=p.id,
            category=p.category.value,
            description=p.description,
            confidence=p.confidence,
            occurrences=p.occurrences,
            pattern_data=p.pattern_data,
        )
        for p in patterns
    ]


# Get metrics
@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    user: dict = Depends(get_current_user),
    learner: Learner = Depends(get_learner_instance),
):
    """Get learning metrics."""
    metrics = await learner.get_metrics(user_id=user["user_id"])

    return MetricsResponse(
        total_interactions=metrics.total_interactions,
        successful_interactions=metrics.successful_interactions,
        failed_interactions=metrics.failed_interactions,
        positive_feedback_count=metrics.positive_feedback_count,
        negative_feedback_count=metrics.negative_feedback_count,
        patterns_learned=metrics.patterns_learned,
        avg_response_time_ms=metrics.avg_response_time_ms,
        success_rate=metrics.success_rate,
        improvement_trend=metrics.improvement_trend,
    )


# Get global metrics (admin)
@app.get("/metrics/global", response_model=MetricsResponse)
async def get_global_metrics(
    learner: Learner = Depends(get_learner_instance),
):
    """Get global learning metrics (all users)."""
    metrics = await learner.get_metrics()

    return MetricsResponse(
        total_interactions=metrics.total_interactions,
        successful_interactions=metrics.successful_interactions,
        failed_interactions=metrics.failed_interactions,
        positive_feedback_count=metrics.positive_feedback_count,
        negative_feedback_count=metrics.negative_feedback_count,
        patterns_learned=metrics.patterns_learned,
        avg_response_time_ms=metrics.avg_response_time_ms,
        success_rate=metrics.success_rate,
        improvement_trend=metrics.improvement_trend,
    )


# Self-reflection
@app.post("/reflect", response_model=ReflectionResponse)
async def reflect(
    period_hours: int = 24,
    user: dict = Depends(get_current_user),
    learner: Learner = Depends(get_learner_instance),
):
    """Generate a self-reflection report."""
    report = await learner.reflect(
        period_hours=period_hours,
        user_id=user["user_id"],
    )

    return ReflectionResponse(
        id=report.id,
        timestamp=report.timestamp,
        period_start=report.period_start,
        period_end=report.period_end,
        metrics=MetricsResponse(
            total_interactions=report.metrics.total_interactions,
            successful_interactions=report.metrics.successful_interactions,
            failed_interactions=report.metrics.failed_interactions,
            positive_feedback_count=report.metrics.positive_feedback_count,
            negative_feedback_count=report.metrics.negative_feedback_count,
            patterns_learned=report.metrics.patterns_learned,
            avg_response_time_ms=report.metrics.avg_response_time_ms,
            success_rate=report.metrics.success_rate,
            improvement_trend=report.metrics.improvement_trend,
        ),
        insights=report.insights,
        improvements_suggested=report.improvements_suggested,
        action_items=report.action_items,
        patterns_count=len(report.patterns_identified),
    )


# Get latest reflection
@app.get("/reflect/latest", response_model=Optional[ReflectionResponse])
async def get_latest_reflection(
    user: dict = Depends(get_current_user),
    learner: Learner = Depends(get_learner_instance),
):
    """Get the most recent reflection report."""
    db = await learner.get_db()
    report = await db.get_latest_reflection()

    if not report:
        return None

    return ReflectionResponse(
        id=report.id,
        timestamp=report.timestamp,
        period_start=report.period_start,
        period_end=report.period_end,
        metrics=MetricsResponse(
            total_interactions=report.metrics.total_interactions,
            successful_interactions=report.metrics.successful_interactions,
            failed_interactions=report.metrics.failed_interactions,
            positive_feedback_count=report.metrics.positive_feedback_count,
            negative_feedback_count=report.metrics.negative_feedback_count,
            patterns_learned=report.metrics.patterns_learned,
            avg_response_time_ms=report.metrics.avg_response_time_ms,
            success_rate=report.metrics.success_rate,
            improvement_trend=report.metrics.improvement_trend,
        ),
        insights=report.insights,
        improvements_suggested=report.improvements_suggested,
        action_items=report.action_items,
        patterns_count=len(report.patterns_identified),
    )


# Update interaction outcome
@app.patch("/interaction/{interaction_id}/outcome")
async def update_outcome(
    interaction_id: str,
    outcome: str,
    user: dict = Depends(get_current_user),
    learner: Learner = Depends(get_learner_instance),
):
    """Update the outcome of an interaction."""
    try:
        outcome_enum = InteractionOutcome(outcome)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid outcome")

    db = await learner.get_db()
    await db.update_interaction_outcome(interaction_id, outcome_enum)

    return {"status": "updated", "interaction_id": interaction_id, "outcome": outcome}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
