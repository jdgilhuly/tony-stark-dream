"""Tests for the orchestration service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.orchestrator import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskResult,
    Workflow,
    WorkflowStatus,
    TaskExecutor,
    Orchestrator,
    get_orchestrator,
)


class TestTask:
    """Test Task dataclass."""

    def test_task_creation(self):
        """Test creating a task with defaults."""
        task = Task(
            id="test-1",
            name="Test Task",
            description="A test task",
            task_type="claude",
            parameters={"action": "ask", "question": "Hello"},
        )

        assert task.id == "test-1"
        assert task.name == "Test Task"
        assert task.task_type == "claude"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL
        assert task.dependencies == []
        assert task.timeout == 300
        assert task.max_retries == 3

    def test_task_with_dependencies(self):
        """Test task with dependencies."""
        task = Task(
            id="test-2",
            name="Dependent Task",
            description="Depends on other tasks",
            task_type="code",
            parameters={"action": "read"},
            dependencies=["task-1", "task-2"],
        )

        assert task.dependencies == ["task-1", "task-2"]

    def test_task_priority_levels(self):
        """Test different priority levels."""
        low = Task(
            id="low",
            name="Low",
            description="Low priority",
            task_type="claude",
            parameters={},
            priority=TaskPriority.LOW,
        )
        high = Task(
            id="high",
            name="High",
            description="High priority",
            task_type="claude",
            parameters={},
            priority=TaskPriority.HIGH,
        )
        critical = Task(
            id="critical",
            name="Critical",
            description="Critical priority",
            task_type="claude",
            parameters={},
            priority=TaskPriority.CRITICAL,
        )

        assert low.priority == TaskPriority.LOW
        assert high.priority == TaskPriority.HIGH
        assert critical.priority == TaskPriority.CRITICAL


class TestTaskResult:
    """Test TaskResult dataclass."""

    def test_successful_result(self):
        """Test successful task result."""
        result = TaskResult(
            success=True,
            output={"response": "Hello!"},
            execution_time_ms=150.5,
        )

        assert result.success is True
        assert result.output == {"response": "Hello!"}
        assert result.error is None
        assert result.execution_time_ms == 150.5

    def test_failed_result(self):
        """Test failed task result."""
        result = TaskResult(
            success=False,
            output=None,
            error="Connection timeout",
            retries=2,
        )

        assert result.success is False
        assert result.error == "Connection timeout"
        assert result.retries == 2


class TestWorkflow:
    """Test Workflow dataclass."""

    def test_workflow_creation(self):
        """Test creating a workflow."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="First task",
                task_type="claude",
                parameters={},
            ),
            Task(
                id="t2",
                name="Task 2",
                description="Second task",
                task_type="code",
                parameters={},
                dependencies=["t1"],
            ),
        ]

        workflow = Workflow(
            id="wf-1",
            name="Test Workflow",
            description="A test workflow",
            tasks=tasks,
        )

        assert workflow.id == "wf-1"
        assert workflow.name == "Test Workflow"
        assert len(workflow.tasks) == 2
        assert workflow.status == WorkflowStatus.PENDING
        assert workflow.results == {}


class TestTaskExecutor:
    """Test TaskExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create a task executor."""
        return TaskExecutor(auth_token="test-token")

    @pytest.mark.asyncio
    async def test_execute_claude_task(self, executor):
        """Test executing a Claude task."""
        task = Task(
            id="claude-1",
            name="Ask Claude",
            description="Ask a question",
            task_type="claude",
            parameters={"action": "ask", "question": "Hello"},
        )

        with patch.object(executor.client, "execute", new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "response": "Hello!"}
            result = await executor.execute(task)

            assert result.success is True
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_code_task(self, executor):
        """Test executing a code task."""
        task = Task(
            id="code-1",
            name="Read File",
            description="Read a file",
            task_type="code",
            parameters={"action": "read_file", "path": "/tmp/test.txt"},
        )

        with patch.object(executor.client, "execute", new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "content": "file contents"}
            result = await executor.execute(task)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_browser_task(self, executor):
        """Test executing a browser task."""
        task = Task(
            id="browser-1",
            name="Scrape Page",
            description="Scrape a web page",
            task_type="browser",
            parameters={"action": "scrape", "url": "https://example.com"},
        )

        with patch.object(executor.client, "execute", new_callable=AsyncMock) as mock:
            mock.return_value = {"success": True, "content": "<html>...</html>"}
            result = await executor.execute(task)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, executor):
        """Test task execution with timeout."""
        task = Task(
            id="timeout-1",
            name="Slow Task",
            description="A slow task",
            task_type="claude",
            parameters={},
            timeout=1,  # 1 second timeout
        )

        with patch.object(executor.client, "execute", new_callable=AsyncMock) as mock:
            import asyncio

            async def slow_execute(*args, **kwargs):
                await asyncio.sleep(5)
                return {"success": True}

            mock.side_effect = slow_execute

            result = await executor.execute(task)
            # Should fail due to timeout
            assert result.success is False
            assert "timeout" in result.error.lower() or "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, executor):
        """Test task execution with retry on failure."""
        task = Task(
            id="retry-1",
            name="Flaky Task",
            description="A flaky task",
            task_type="claude",
            parameters={},
            max_retries=2,
        )

        call_count = 0

        async def flaky_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return {"success": True, "response": "Finally worked!"}

        with patch.object(executor.client, "execute", new_callable=AsyncMock) as mock:
            mock.side_effect = flaky_execute
            result = await executor.execute(task)

            # Should succeed after retry
            assert result.success is True
            assert result.retries == 1


class TestOrchestrator:
    """Test Orchestrator class."""

    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator."""
        return Orchestrator(auth_token="test-token")

    def test_create_workflow(self, orchestrator):
        """Test creating a workflow."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="First",
                task_type="claude",
                parameters={},
            ),
        ]

        workflow = orchestrator.create_workflow(
            name="Test Workflow",
            description="Test",
            tasks=tasks,
        )

        assert workflow.name == "Test Workflow"
        assert len(workflow.tasks) == 1
        assert workflow.id in orchestrator.workflows

    def test_create_workflow_validates_dependencies(self, orchestrator):
        """Test that workflow creation validates dependencies."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="First",
                task_type="claude",
                parameters={},
                dependencies=["nonexistent"],  # Invalid dependency
            ),
        ]

        with pytest.raises(ValueError, match="dependency"):
            orchestrator.create_workflow(
                name="Invalid Workflow",
                description="Test",
                tasks=tasks,
            )

    def test_create_workflow_detects_cycles(self, orchestrator):
        """Test that workflow creation detects circular dependencies."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="First",
                task_type="claude",
                parameters={},
                dependencies=["t2"],
            ),
            Task(
                id="t2",
                name="Task 2",
                description="Second",
                task_type="claude",
                parameters={},
                dependencies=["t1"],
            ),
        ]

        with pytest.raises(ValueError, match="[Cc]ircular|cycle"):
            orchestrator.create_workflow(
                name="Circular Workflow",
                description="Test",
                tasks=tasks,
            )

    @pytest.mark.asyncio
    async def test_execute_single_task(self, orchestrator):
        """Test executing a single task."""
        task = Task(
            id="single-1",
            name="Single Task",
            description="A single task",
            task_type="claude",
            parameters={"action": "ask", "question": "Hello"},
        )

        with patch.object(
            orchestrator.executor, "execute", new_callable=AsyncMock
        ) as mock:
            mock.return_value = TaskResult(
                success=True, output={"response": "Hi!"}, execution_time_ms=100
            )

            result = await orchestrator.execute_single_task(task)

            assert result.success is True
            mock.assert_called_once_with(task)

    @pytest.mark.asyncio
    async def test_execute_workflow_sequential(self, orchestrator):
        """Test executing a workflow with sequential tasks."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="First",
                task_type="claude",
                parameters={},
            ),
            Task(
                id="t2",
                name="Task 2",
                description="Second",
                task_type="code",
                parameters={},
                dependencies=["t1"],
            ),
        ]

        workflow = orchestrator.create_workflow(
            name="Sequential",
            description="Sequential workflow",
            tasks=tasks,
        )

        execution_order = []

        async def mock_execute(task):
            execution_order.append(task.id)
            return TaskResult(success=True, output={}, execution_time_ms=50)

        with patch.object(
            orchestrator.executor, "execute", side_effect=mock_execute
        ):
            completed = await orchestrator.execute_workflow(workflow.id)

            assert completed.status == WorkflowStatus.COMPLETED
            assert execution_order == ["t1", "t2"]
            assert len(completed.results) == 2

    @pytest.mark.asyncio
    async def test_execute_workflow_parallel(self, orchestrator):
        """Test executing a workflow with parallel tasks."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="First",
                task_type="claude",
                parameters={},
            ),
            Task(
                id="t2",
                name="Task 2",
                description="Second (parallel)",
                task_type="code",
                parameters={},
            ),
            Task(
                id="t3",
                name="Task 3",
                description="Third (depends on both)",
                task_type="browser",
                parameters={},
                dependencies=["t1", "t2"],
            ),
        ]

        workflow = orchestrator.create_workflow(
            name="Parallel",
            description="Parallel workflow",
            tasks=tasks,
        )

        with patch.object(orchestrator.executor, "execute", new_callable=AsyncMock) as mock:
            mock.return_value = TaskResult(success=True, output={}, execution_time_ms=50)

            completed = await orchestrator.execute_workflow(workflow.id)

            assert completed.status == WorkflowStatus.COMPLETED
            assert len(completed.results) == 3

    @pytest.mark.asyncio
    async def test_execute_workflow_with_failure(self, orchestrator):
        """Test workflow execution when a task fails."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="Will fail",
                task_type="claude",
                parameters={},
            ),
            Task(
                id="t2",
                name="Task 2",
                description="Depends on failed task",
                task_type="code",
                parameters={},
                dependencies=["t1"],
            ),
        ]

        workflow = orchestrator.create_workflow(
            name="Failing",
            description="Failing workflow",
            tasks=tasks,
        )

        with patch.object(orchestrator.executor, "execute", new_callable=AsyncMock) as mock:
            mock.return_value = TaskResult(
                success=False, output=None, error="Task failed", execution_time_ms=50
            )

            completed = await orchestrator.execute_workflow(workflow.id)

            # Workflow should be marked as failed
            assert completed.status == WorkflowStatus.FAILED

    def test_get_workflow(self, orchestrator):
        """Test getting a workflow by ID."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="First",
                task_type="claude",
                parameters={},
            ),
        ]

        workflow = orchestrator.create_workflow(
            name="Test",
            description="Test",
            tasks=tasks,
        )

        retrieved = orchestrator.get_workflow(workflow.id)
        assert retrieved is not None
        assert retrieved.id == workflow.id

        # Non-existent workflow
        assert orchestrator.get_workflow("nonexistent") is None

    def test_cancel_workflow(self, orchestrator):
        """Test cancelling a workflow."""
        tasks = [
            Task(
                id="t1",
                name="Task 1",
                description="First",
                task_type="claude",
                parameters={},
            ),
        ]

        workflow = orchestrator.create_workflow(
            name="Test",
            description="Test",
            tasks=tasks,
        )

        # Start workflow (set to running)
        workflow.status = WorkflowStatus.RUNNING

        success = orchestrator.cancel_workflow(workflow.id)
        assert success is True

        retrieved = orchestrator.get_workflow(workflow.id)
        assert retrieved.status == WorkflowStatus.CANCELLED


class TestGetOrchestrator:
    """Test get_orchestrator function."""

    def test_get_orchestrator_creates_instance(self):
        """Test that get_orchestrator creates an orchestrator."""
        orchestrator = get_orchestrator("test-token")
        assert orchestrator is not None
        assert isinstance(orchestrator, Orchestrator)

    def test_get_orchestrator_caches_by_token(self):
        """Test that orchestrators are cached by token."""
        orch1 = get_orchestrator("token-1")
        orch2 = get_orchestrator("token-1")
        orch3 = get_orchestrator("token-2")

        assert orch1 is orch2  # Same token, same instance
        assert orch1 is not orch3  # Different token, different instance
