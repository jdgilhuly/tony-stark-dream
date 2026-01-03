"""JARVIS Task Execution Service - Command execution and automation."""

import logging
import uuid
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Any
from functools import lru_cache
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import redis.asyncio as redis
from jose import jwt, JWTError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    service_name: str = "task-execution"
    host: str = "0.0.0.0"
    port: int = 8007

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://jarvis:jarvis@localhost:5432/jarvis"

    jwt_secret: str = "development-secret-change-in-production"
    jwt_algorithm: str = "HS256"

    # Service URLs for task execution
    conversation_service_url: str = "http://localhost:8001"
    briefing_service_url: str = "http://localhost:8005"
    notification_service_url: str = "http://localhost:8008"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


# Enums
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    REMINDER = "reminder"
    SCHEDULED_BRIEFING = "scheduled_briefing"
    AUTOMATION = "automation"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


# Models
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: Optional[str] = None
    type: TaskType = TaskType.CUSTOM
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    payload: dict = Field(default_factory=dict)
    schedule: Optional[str] = None  # Cron expression
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[dict] = None


class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    type: TaskType = TaskType.CUSTOM
    priority: TaskPriority = TaskPriority.MEDIUM
    payload: dict = Field(default_factory=dict)
    schedule: Optional[str] = None
    due_date: Optional[datetime] = None


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None


# Redis client
_redis: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


# Auth
async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {"user_id": payload.get("userId")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# Task storage
class TaskStore:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def init(self):
        self.redis = await get_redis()

    def _key(self, task_id: str) -> str:
        return f"task:{task_id}"

    def _user_key(self, user_id: str) -> str:
        return f"user:{user_id}:tasks"

    async def save(self, task: Task) -> None:
        task.updated_at = datetime.utcnow()
        await self.redis.set(self._key(task.id), task.model_dump_json())
        await self.redis.sadd(self._user_key(task.user_id), task.id)

    async def get(self, task_id: str) -> Optional[Task]:
        data = await self.redis.get(self._key(task_id))
        if data:
            return Task.model_validate_json(data)
        return None

    async def delete(self, task: Task) -> None:
        await self.redis.delete(self._key(task.id))
        await self.redis.srem(self._user_key(task.user_id), task.id)

    async def get_user_tasks(self, user_id: str) -> list[Task]:
        task_ids = await self.redis.smembers(self._user_key(user_id))
        tasks = []
        for tid in task_ids:
            task = await self.get(tid)
            if task:
                tasks.append(task)
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    async def get_pending_tasks(self, user_id: str) -> list[Task]:
        tasks = await self.get_user_tasks(user_id)
        return [t for t in tasks if t.status == TaskStatus.PENDING]


task_store = TaskStore()

# Scheduler
scheduler = AsyncIOScheduler()


# Task executors
async def execute_reminder(task: Task) -> dict:
    """Execute a reminder task."""
    logger.info(f"Executing reminder: {task.title}")
    # In production, this would send a notification
    return {"message": f"Reminder: {task.title}", "notified": True}


async def execute_scheduled_briefing(task: Task) -> dict:
    """Execute a scheduled briefing."""
    import httpx

    logger.info(f"Generating scheduled briefing for user {task.user_id}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # This would use a service token in production
            resp = await client.post(
                f"{settings.briefing_service_url}/briefing/generate",
                json=task.payload,
                headers={"Authorization": f"Bearer {task.payload.get('token', '')}"}
            )
            if resp.status_code == 200:
                return {"briefing_generated": True, "data": resp.json()}
    except Exception as e:
        logger.error(f"Briefing generation failed: {e}")
        raise

    return {"briefing_generated": False}


async def execute_automation(task: Task) -> dict:
    """Execute an automation task."""
    action = task.payload.get("action")
    params = task.payload.get("params", {})

    logger.info(f"Executing automation: {action}")

    # Add automation handlers here
    automations = {
        "send_notification": lambda p: {"sent": True, "message": p.get("message")},
        "log_event": lambda p: {"logged": True, "event": p.get("event")},
    }

    handler = automations.get(action)
    if handler:
        return handler(params)

    return {"executed": False, "error": f"Unknown action: {action}"}


async def execute_task(task: Task) -> None:
    """Execute a task based on its type."""
    task.status = TaskStatus.RUNNING
    await task_store.save(task)

    try:
        if task.type == TaskType.REMINDER:
            result = await execute_reminder(task)
        elif task.type == TaskType.SCHEDULED_BRIEFING:
            result = await execute_scheduled_briefing(task)
        elif task.type == TaskType.AUTOMATION:
            result = await execute_automation(task)
        else:
            result = {"executed": True, "type": task.type}

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.result = result

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
        logger.error(f"Task {task.id} failed: {e}")

    await task_store.save(task)


def schedule_task(task: Task) -> None:
    """Schedule a task with cron expression."""
    if not task.schedule:
        return

    try:
        trigger = CronTrigger.from_crontab(task.schedule)
        scheduler.add_job(
            execute_task,
            trigger,
            args=[task],
            id=f"task_{task.id}",
            replace_existing=True
        )
        logger.info(f"Scheduled task {task.id} with cron: {task.schedule}")
    except Exception as e:
        logger.error(f"Failed to schedule task {task.id}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.service_name}")
    await task_store.init()
    scheduler.start()
    yield
    scheduler.shutdown()
    if _redis:
        await _redis.close()
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Task Execution Service",
    description="Command execution and task automation",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
        "scheduled_jobs": len(scheduler.get_jobs())
    }


@app.post("/tasks", response_model=Task)
async def create_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Create a new task."""
    task = Task(
        user_id=user["user_id"],
        title=request.title,
        description=request.description,
        type=request.type,
        priority=request.priority,
        payload=request.payload,
        schedule=request.schedule,
        due_date=request.due_date
    )

    await task_store.save(task)

    # Schedule if cron expression provided
    if task.schedule:
        schedule_task(task)
    # Execute immediately if no schedule and no due date
    elif not task.due_date:
        background_tasks.add_task(execute_task, task)

    logger.info(f"Created task {task.id} for user {user['user_id']}")
    return task


@app.get("/tasks", response_model=list[Task])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    type: Optional[TaskType] = None,
    priority: Optional[TaskPriority] = None,
    user: dict = Depends(get_current_user)
):
    """List user's tasks with optional filters."""
    tasks = await task_store.get_user_tasks(user["user_id"])

    if status:
        tasks = [t for t in tasks if t.status == status]
    if type:
        tasks = [t for t in tasks if t.type == type]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]

    return tasks


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a specific task."""
    task = await task_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return task


@app.patch("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    user: dict = Depends(get_current_user)
):
    """Update a task."""
    task = await task_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if request.title is not None:
        task.title = request.title
    if request.description is not None:
        task.description = request.description
    if request.priority is not None:
        task.priority = request.priority
    if request.status is not None:
        task.status = request.status
    if request.due_date is not None:
        task.due_date = request.due_date

    await task_store.save(task)
    return task


@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a task."""
    task = await task_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Remove from scheduler if scheduled
    try:
        scheduler.remove_job(f"task_{task_id}")
    except Exception:
        pass

    await task_store.delete(task)
    return {"success": True}


@app.post("/tasks/{task_id}/execute")
async def execute_task_now(
    task_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Execute a task immediately."""
    task = await task_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Task is already running")

    background_tasks.add_task(execute_task, task)
    return {"success": True, "message": "Task execution started"}


@app.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    user: dict = Depends(get_current_user)
):
    """Cancel a pending or scheduled task."""
    task = await task_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")

    task.status = TaskStatus.CANCELLED
    await task_store.save(task)

    # Remove from scheduler
    try:
        scheduler.remove_job(f"task_{task_id}")
    except Exception:
        pass

    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
