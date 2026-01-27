"""
Task Orchestrator

Coordinates complex multi-step tasks and agent workflows.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import httpx
import networkx as nx

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskResult:
    """Result of a task execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0
    retries: int = 0


@dataclass
class Task:
    """A task to be executed."""
    id: str
    name: str
    description: str
    task_type: str  # claude, code, browser, research, github, custom
    parameters: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[TaskResult] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # seconds
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    """A workflow containing multiple tasks."""
    id: str
    name: str
    description: str
    tasks: List[Task]
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, TaskResult] = field(default_factory=dict)


class ServiceClient:
    """Client for calling other JARVIS services."""

    def __init__(
        self,
        claude_url: str,
        code_url: str,
        browser_url: str,
        memory_url: str,
        research_url: str,
        github_url: str,
        timeout: int = 120,
    ):
        self.service_urls = {
            "claude": claude_url,
            "code": code_url,
            "browser": browser_url,
            "memory": memory_url,
            "research": research_url,
            "github": github_url,
        }
        self.timeout = timeout

    async def call(
        self,
        service: str,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Call a service endpoint."""
        base_url = self.service_urls.get(service)
        if not base_url:
            raise ValueError(f"Unknown service: {service}")

        url = f"{base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(
                    url, params=params, headers=headers, timeout=self.timeout
                )
            elif method.upper() == "POST":
                response = await client.post(
                    url, json=data, params=params, headers=headers, timeout=self.timeout
                )
            elif method.upper() == "PUT":
                response = await client.put(
                    url, json=data, params=params, headers=headers, timeout=self.timeout
                )
            elif method.upper() == "DELETE":
                response = await client.delete(
                    url, params=params, headers=headers, timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()


class TaskExecutor:
    """Executes individual tasks."""

    def __init__(self, service_client: ServiceClient, auth_token: str):
        self.client = service_client
        self.auth_token = auth_token
        self._handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default task handlers."""
        self._handlers["claude"] = self._execute_claude_task
        self._handlers["code"] = self._execute_code_task
        self._handlers["browser"] = self._execute_browser_task
        self._handlers["research"] = self._execute_research_task
        self._handlers["github"] = self._execute_github_task
        self._handlers["memory"] = self._execute_memory_task

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a custom task handler."""
        self._handlers[task_type] = handler

    async def execute(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Execute a task."""
        start_time = datetime.utcnow()

        handler = self._handlers.get(task.task_type)
        if not handler:
            return TaskResult(
                success=False,
                output=None,
                error=f"Unknown task type: {task.task_type}",
            )

        try:
            # Inject context into parameters
            params = {**task.parameters}
            params["_context"] = context

            output = await asyncio.wait_for(
                handler(params),
                timeout=task.timeout,
            )

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return TaskResult(
                success=True,
                output=output,
                execution_time_ms=execution_time,
                retries=task.retry_count,
            )

        except asyncio.TimeoutError:
            return TaskResult(
                success=False,
                output=None,
                error=f"Task timed out after {task.timeout} seconds",
                retries=task.retry_count,
            )
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            return TaskResult(
                success=False,
                output=None,
                error=str(e),
                retries=task.retry_count,
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get auth headers for service calls."""
        return {"Authorization": f"Bearer {self.auth_token}"}

    async def _execute_claude_task(self, params: Dict[str, Any]) -> Any:
        """Execute a Claude API task."""
        action = params.get("action", "chat")
        headers = self._get_headers()

        if action == "chat":
            return await self.client.call(
                "claude",
                "/chat",
                data={
                    "messages": params.get("messages", []),
                    "system": params.get("system"),
                },
                headers=headers,
            )
        elif action == "code":
            return await self.client.call(
                "claude",
                "/code",
                data={
                    "task": params.get("task"),
                    "working_directory": params.get("working_directory", "."),
                },
                headers=headers,
            )
        elif action == "ask":
            return await self.client.call(
                "claude",
                "/ask",
                params={
                    "question": params.get("question"),
                    "use_tools": params.get("use_tools", True),
                },
                headers=headers,
            )

    async def _execute_code_task(self, params: Dict[str, Any]) -> Any:
        """Execute a code service task."""
        action = params.get("action")
        headers = self._get_headers()

        if action == "read":
            return await self.client.call(
                "code",
                "/file",
                method="GET",
                params={"path": params.get("path")},
                headers=headers,
            )
        elif action == "write":
            return await self.client.call(
                "code",
                "/file",
                data={
                    "path": params.get("path"),
                    "content": params.get("content"),
                },
                headers=headers,
            )
        elif action == "execute":
            return await self.client.call(
                "code",
                "/execute",
                data={
                    "code": params.get("code"),
                    "language": params.get("language", "python"),
                    "timeout": params.get("timeout", 30),
                },
                headers=headers,
            )
        elif action == "git_status":
            return await self.client.call(
                "code",
                "/git/status",
                method="GET",
                params={"repo_path": params.get("repo_path")},
                headers=headers,
            )

    async def _execute_browser_task(self, params: Dict[str, Any]) -> Any:
        """Execute a browser automation task."""
        action = params.get("action")
        headers = self._get_headers()

        if action == "scrape":
            return await self.client.call(
                "browser",
                "/scrape",
                params={
                    "url": params.get("url"),
                    "include_html": params.get("include_html", False),
                },
                headers=headers,
            )

    async def _execute_research_task(self, params: Dict[str, Any]) -> Any:
        """Execute a research task."""
        action = params.get("action", "research")
        headers = self._get_headers()

        if action == "search":
            return await self.client.call(
                "research",
                "/search",
                data={
                    "query": params.get("query"),
                    "max_results": params.get("max_results", 10),
                },
                headers=headers,
            )
        elif action == "research":
            return await self.client.call(
                "research",
                "/research",
                data={
                    "query": params.get("query"),
                    "max_sources": params.get("max_sources", 5),
                },
                headers=headers,
            )

    async def _execute_github_task(self, params: Dict[str, Any]) -> Any:
        """Execute a GitHub task."""
        action = params.get("action")
        headers = self._get_headers()

        if action == "get_repo":
            return await self.client.call(
                "github",
                f"/repos/{params.get('owner')}/{params.get('repo')}",
                method="GET",
                headers=headers,
            )
        elif action == "create_issue":
            return await self.client.call(
                "github",
                f"/repos/{params.get('owner')}/{params.get('repo')}/issues",
                data={
                    "title": params.get("title"),
                    "body": params.get("body"),
                },
                headers=headers,
            )
        elif action == "create_pr":
            return await self.client.call(
                "github",
                f"/repos/{params.get('owner')}/{params.get('repo')}/pulls",
                data={
                    "title": params.get("title"),
                    "head": params.get("head"),
                    "base": params.get("base"),
                    "body": params.get("body"),
                },
                headers=headers,
            )

    async def _execute_memory_task(self, params: Dict[str, Any]) -> Any:
        """Execute a memory task."""
        action = params.get("action")
        headers = self._get_headers()

        if action == "store":
            return await self.client.call(
                "memory",
                "/memory",
                data={
                    "content": params.get("content"),
                    "memory_type": params.get("memory_type", "fact"),
                    "importance": params.get("importance", 0.5),
                },
                headers=headers,
            )
        elif action == "search":
            return await self.client.call(
                "memory",
                "/memory/search",
                data={
                    "query": params.get("query"),
                    "max_results": params.get("max_results", 10),
                },
                headers=headers,
            )


class Orchestrator:
    """
    Task and workflow orchestrator.

    Features:
    - Task dependency resolution (DAG)
    - Parallel execution
    - Retry logic
    - State management
    - Result aggregation
    """

    def __init__(
        self,
        executor: TaskExecutor,
        max_parallel: int = 5,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.executor = executor
        self.max_parallel = max_parallel
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._workflows: Dict[str, Workflow] = {}
        self._semaphore = asyncio.Semaphore(max_parallel)

    def create_workflow(
        self,
        name: str,
        description: str,
        tasks: List[Task],
    ) -> Workflow:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())

        # Validate task dependencies
        self._validate_dependencies(tasks)

        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            tasks=tasks,
        )

        self._workflows[workflow_id] = workflow
        return workflow

    def _validate_dependencies(self, tasks: List[Task]) -> None:
        """Validate that task dependencies form a valid DAG."""
        task_ids = {t.id for t in tasks}

        # Check all dependencies exist
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ValueError(f"Task {task.id} depends on unknown task {dep}")

        # Check for cycles
        graph = nx.DiGraph()
        for task in tasks:
            graph.add_node(task.id)
            for dep in task.dependencies:
                graph.add_edge(dep, task.id)

        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("Task dependencies contain a cycle")

    def _get_ready_tasks(
        self,
        tasks: List[Task],
        completed: Set[str],
    ) -> List[Task]:
        """Get tasks that are ready to execute."""
        ready = []
        for task in tasks:
            if task.status != TaskStatus.PENDING:
                continue
            if all(dep in completed for dep in task.dependencies):
                ready.append(task)
        return ready

    async def execute_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """Execute a workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        workflow.status = TaskStatus.RUNNING
        workflow.started_at = datetime.utcnow().isoformat()
        workflow.context = context or {}

        completed: Set[str] = set()
        failed: Set[str] = set()

        try:
            while True:
                # Get ready tasks
                ready = self._get_ready_tasks(workflow.tasks, completed)

                if not ready:
                    # Check if all tasks are done
                    pending = [t for t in workflow.tasks if t.status == TaskStatus.PENDING]
                    if not pending:
                        break
                    # Some tasks are blocked by failures
                    if failed:
                        break
                    await asyncio.sleep(0.1)
                    continue

                # Execute ready tasks in parallel
                tasks_to_run = ready[:self.max_parallel]
                results = await asyncio.gather(
                    *[self._execute_task(task, workflow.context) for task in tasks_to_run],
                    return_exceptions=True,
                )

                # Process results
                for task, result in zip(tasks_to_run, results):
                    if isinstance(result, Exception):
                        task.status = TaskStatus.FAILED
                        task.result = TaskResult(success=False, output=None, error=str(result))
                        failed.add(task.id)
                    elif result.success:
                        task.status = TaskStatus.COMPLETED
                        task.result = result
                        completed.add(task.id)
                        # Add to context for dependent tasks
                        workflow.context[f"task_{task.id}_result"] = result.output
                        workflow.results[task.id] = result
                    else:
                        task.status = TaskStatus.FAILED
                        task.result = result
                        failed.add(task.id)
                        workflow.results[task.id] = result

            # Determine final status
            if failed:
                workflow.status = TaskStatus.FAILED
            else:
                workflow.status = TaskStatus.COMPLETED

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            workflow.status = TaskStatus.FAILED

        workflow.completed_at = datetime.utcnow().isoformat()
        return workflow

    async def _execute_task(
        self,
        task: Task,
        context: Dict[str, Any],
    ) -> TaskResult:
        """Execute a single task with retry logic."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow().isoformat()

            for attempt in range(task.max_retries + 1):
                task.retry_count = attempt

                if attempt > 0:
                    task.status = TaskStatus.RETRYING
                    await asyncio.sleep(self.retry_delay * attempt)

                result = await self.executor.execute(task, context)

                if result.success:
                    task.completed_at = datetime.utcnow().isoformat()
                    return result

                if attempt < task.max_retries:
                    logger.warning(
                        f"Task {task.id} failed (attempt {attempt + 1}), retrying..."
                    )

            task.completed_at = datetime.utcnow().isoformat()
            return result

    async def execute_single_task(
        self,
        task: Task,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Execute a single task (not part of a workflow)."""
        return await self._execute_task(task, context or {})

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        if workflow.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False

        workflow.status = TaskStatus.CANCELLED
        for task in workflow.tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
                task.status = TaskStatus.CANCELLED

        return True


# Singleton instances
_service_client: Optional[ServiceClient] = None
_orchestrator: Optional[Orchestrator] = None


def get_service_client() -> ServiceClient:
    """Get or create the service client singleton."""
    global _service_client
    if _service_client is None:
        from .config import get_settings
        settings = get_settings()
        _service_client = ServiceClient(
            claude_url=settings.claude_service_url,
            code_url=settings.code_service_url,
            browser_url=settings.browser_service_url,
            memory_url=settings.memory_service_url,
            research_url=settings.research_service_url,
            github_url=settings.github_service_url,
        )
    return _service_client


def get_orchestrator(auth_token: str) -> Orchestrator:
    """Get or create the orchestrator."""
    from .config import get_settings
    settings = get_settings()

    service_client = get_service_client()
    executor = TaskExecutor(service_client, auth_token)

    return Orchestrator(
        executor=executor,
        max_parallel=settings.max_parallel_tasks,
        max_retries=settings.max_retries,
        retry_delay=settings.retry_delay,
    )
