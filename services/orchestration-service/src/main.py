"""
JARVIS Orchestration Service - Main FastAPI Application

Coordinates multi-step tasks and agent workflows.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .orchestrator import (
    get_orchestrator,
    Task,
    TaskStatus,
    TaskPriority,
    TaskResult,
    Workflow,
)

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
    yield
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS Orchestration Service",
    description="Multi-step task and workflow orchestration",
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
class TaskRequest(BaseModel):
    name: str
    description: str
    task_type: str  # claude, code, browser, research, github, memory
    parameters: Dict[str, Any]
    priority: str = "normal"
    timeout: int = 300
    max_retries: int = 3
    metadata: Dict[str, Any] = {}


class TaskWithDepsRequest(BaseModel):
    id: str
    name: str
    description: str
    task_type: str
    parameters: Dict[str, Any]
    dependencies: List[str] = []
    priority: str = "normal"
    timeout: int = 300
    max_retries: int = 3


class WorkflowRequest(BaseModel):
    name: str
    description: str
    tasks: List[TaskWithDepsRequest]


class TaskResultModel(BaseModel):
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0
    retries: int = 0


class TaskInfoModel(BaseModel):
    id: str
    name: str
    description: str
    task_type: str
    status: str
    priority: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[TaskResultModel] = None


class WorkflowInfoModel(BaseModel):
    id: str
    name: str
    description: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    tasks: List[TaskInfoModel]
    results: Dict[str, TaskResultModel]


# Complex task templates
class CodeTaskRequest(BaseModel):
    task: str  # Natural language description of what to do
    working_directory: str = "."
    use_git: bool = True


class ResearchTaskRequest(BaseModel):
    topic: str
    depth: str = "moderate"  # shallow, moderate, deep
    include_sources: bool = True
    save_to_memory: bool = True


class AutomationTaskRequest(BaseModel):
    description: str
    url: Optional[str] = None
    steps: Optional[List[str]] = None


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


def task_to_model(task: Task) -> TaskInfoModel:
    """Convert Task to response model."""
    return TaskInfoModel(
        id=task.id,
        name=task.name,
        description=task.description,
        task_type=task.task_type,
        status=task.status.value,
        priority=task.priority.value,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        result=TaskResultModel(**task.result.__dict__) if task.result else None,
    )


def workflow_to_model(workflow: Workflow) -> WorkflowInfoModel:
    """Convert Workflow to response model."""
    return WorkflowInfoModel(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status.value,
        created_at=workflow.created_at,
        started_at=workflow.started_at,
        completed_at=workflow.completed_at,
        tasks=[task_to_model(t) for t in workflow.tasks],
        results={
            k: TaskResultModel(**v.__dict__)
            for k, v in workflow.results.items()
        },
    )


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Single task execution
@app.post("/task", response_model=TaskResultModel)
async def execute_task(
    request: TaskRequest,
    user: dict = Depends(get_current_user),
):
    """Execute a single task."""
    try:
        import uuid

        task = Task(
            id=str(uuid.uuid4()),
            name=request.name,
            description=request.description,
            task_type=request.task_type,
            parameters=request.parameters,
            priority=TaskPriority(request.priority),
            timeout=request.timeout,
            max_retries=request.max_retries,
            metadata=request.metadata,
        )

        orchestrator = get_orchestrator(user["token"])
        result = await orchestrator.execute_single_task(task)

        return TaskResultModel(**result.__dict__)

    except Exception as e:
        logger.error(f"Task execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Workflow execution
@app.post("/workflow", response_model=WorkflowInfoModel)
async def create_and_execute_workflow(
    request: WorkflowRequest,
    user: dict = Depends(get_current_user),
):
    """Create and execute a workflow."""
    try:
        # Convert request tasks to Task objects
        tasks = []
        for t in request.tasks:
            tasks.append(Task(
                id=t.id,
                name=t.name,
                description=t.description,
                task_type=t.task_type,
                parameters=t.parameters,
                dependencies=t.dependencies,
                priority=TaskPriority(t.priority),
                timeout=t.timeout,
                max_retries=t.max_retries,
            ))

        orchestrator = get_orchestrator(user["token"])
        workflow = orchestrator.create_workflow(
            name=request.name,
            description=request.description,
            tasks=tasks,
        )

        # Execute the workflow
        completed_workflow = await orchestrator.execute_workflow(workflow.id)

        return workflow_to_model(completed_workflow)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Workflow execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workflow/{workflow_id}", response_model=WorkflowInfoModel)
async def get_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
):
    """Get workflow status."""
    orchestrator = get_orchestrator(user["token"])
    workflow = orchestrator.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return workflow_to_model(workflow)


@app.delete("/workflow/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    user: dict = Depends(get_current_user),
):
    """Cancel a running workflow."""
    orchestrator = get_orchestrator(user["token"])
    success = orchestrator.cancel_workflow(workflow_id)

    if not success:
        raise HTTPException(status_code=400, detail="Could not cancel workflow")

    return {"status": "cancelled", "workflow_id": workflow_id}


# High-level task templates
@app.post("/code-task")
async def execute_code_task(
    request: CodeTaskRequest,
    user: dict = Depends(get_current_user),
):
    """
    Execute a coding task.
    Uses Claude with code tools to complete the task.
    """
    try:
        import uuid

        tasks = []

        # Task 1: Use Claude to analyze and plan
        tasks.append(Task(
            id="plan",
            name="Plan task",
            description="Analyze the coding task and create a plan",
            task_type="claude",
            parameters={
                "action": "ask",
                "question": f"Analyze this coding task and create a plan: {request.task}",
                "use_tools": False,
            },
        ))

        # Task 2: Execute the coding task
        tasks.append(Task(
            id="execute",
            name="Execute code task",
            description="Execute the coding task using Claude with tools",
            task_type="claude",
            parameters={
                "action": "code",
                "task": request.task,
                "working_directory": request.working_directory,
            },
            dependencies=["plan"],
        ))

        # Task 3: Git commit if enabled
        if request.use_git:
            tasks.append(Task(
                id="git_status",
                name="Check git status",
                description="Check git status after changes",
                task_type="code",
                parameters={
                    "action": "git_status",
                    "repo_path": request.working_directory,
                },
                dependencies=["execute"],
            ))

        orchestrator = get_orchestrator(user["token"])
        workflow = orchestrator.create_workflow(
            name=f"Code Task: {request.task[:50]}",
            description=request.task,
            tasks=tasks,
        )

        completed = await orchestrator.execute_workflow(workflow.id)
        return workflow_to_model(completed)

    except Exception as e:
        logger.error(f"Code task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research-task")
async def execute_research_task(
    request: ResearchTaskRequest,
    user: dict = Depends(get_current_user),
):
    """
    Execute a research task.
    Searches the web, extracts content, and synthesizes findings.
    """
    try:
        import uuid

        max_sources = {"shallow": 3, "moderate": 5, "deep": 10}.get(request.depth, 5)

        tasks = []

        # Task 1: Research
        tasks.append(Task(
            id="research",
            name="Conduct research",
            description=f"Research: {request.topic}",
            task_type="research",
            parameters={
                "action": "research",
                "query": request.topic,
                "max_sources": max_sources,
            },
        ))

        # Task 2: Synthesize with Claude
        tasks.append(Task(
            id="synthesize",
            name="Synthesize findings",
            description="Synthesize research findings",
            task_type="claude",
            parameters={
                "action": "ask",
                "question": f"Based on the research about '{request.topic}', provide a comprehensive summary of key findings, insights, and conclusions.",
                "use_tools": False,
            },
            dependencies=["research"],
        ))

        # Task 3: Save to memory if enabled
        if request.save_to_memory:
            tasks.append(Task(
                id="save_memory",
                name="Save to memory",
                description="Save research findings to memory",
                task_type="memory",
                parameters={
                    "action": "store",
                    "content": f"Research on: {request.topic}",
                    "memory_type": "fact",
                    "importance": 0.7,
                },
                dependencies=["synthesize"],
            ))

        orchestrator = get_orchestrator(user["token"])
        workflow = orchestrator.create_workflow(
            name=f"Research: {request.topic[:50]}",
            description=f"Research task on: {request.topic}",
            tasks=tasks,
        )

        completed = await orchestrator.execute_workflow(workflow.id)
        return workflow_to_model(completed)

    except Exception as e:
        logger.error(f"Research task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/automation-task")
async def execute_automation_task(
    request: AutomationTaskRequest,
    user: dict = Depends(get_current_user),
):
    """
    Execute a browser automation task.
    """
    try:
        import uuid

        tasks = []

        if request.url:
            # Task: Scrape URL
            tasks.append(Task(
                id="scrape",
                name="Scrape URL",
                description=f"Scrape content from {request.url}",
                task_type="browser",
                parameters={
                    "action": "scrape",
                    "url": request.url,
                },
            ))

        # Task: Analyze with Claude
        tasks.append(Task(
            id="analyze",
            name="Analyze task",
            description="Analyze automation task",
            task_type="claude",
            parameters={
                "action": "ask",
                "question": f"Analyze this automation task and suggest how to complete it: {request.description}",
                "use_tools": True,
            },
            dependencies=["scrape"] if request.url else [],
        ))

        orchestrator = get_orchestrator(user["token"])
        workflow = orchestrator.create_workflow(
            name=f"Automation: {request.description[:50]}",
            description=request.description,
            tasks=tasks,
        )

        completed = await orchestrator.execute_workflow(workflow.id)
        return workflow_to_model(completed)

    except Exception as e:
        logger.error(f"Automation task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Simple execution shortcuts
@app.post("/do")
async def do_task(
    task: str,
    user: dict = Depends(get_current_user),
):
    """
    Natural language task execution.
    Automatically routes to appropriate service/workflow.
    """
    try:
        import uuid

        # Use Claude to understand and execute the task
        orchestrator = get_orchestrator(user["token"])

        simple_task = Task(
            id=str(uuid.uuid4()),
            name="Do task",
            description=task,
            task_type="claude",
            parameters={
                "action": "ask",
                "question": task,
                "use_tools": True,
            },
            timeout=300,
        )

        result = await orchestrator.execute_single_task(simple_task)

        return {
            "task": task,
            "success": result.success,
            "result": result.output,
            "error": result.error,
        }

    except Exception as e:
        logger.error(f"Do task error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
