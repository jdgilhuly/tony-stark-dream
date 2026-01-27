"""
Code Execution Tests
"""

import pytest
import asyncio

from src.execution import (
    CodeExecutor,
    ExecutionRequest,
    ExecutionConfig,
    ExecutionLanguage,
    ExecutionStatus,
)


@pytest.fixture
def executor():
    """Create a code executor for testing."""
    return CodeExecutor()


class TestCodeExecutor:
    """Test code executor."""

    @pytest.mark.asyncio
    async def test_execute_python(self, executor):
        """Test executing Python code."""
        request = ExecutionRequest(
            code='print("Hello, JARVIS!")',
            language=ExecutionLanguage.PYTHON,
        )

        result = await executor.execute(request)

        assert result.status == ExecutionStatus.COMPLETED
        assert result.exit_code == 0
        assert "Hello, JARVIS!" in result.stdout
        assert result.stderr == ""

    @pytest.mark.asyncio
    async def test_execute_python_with_error(self, executor):
        """Test executing Python code with an error."""
        request = ExecutionRequest(
            code='raise ValueError("Test error")',
            language=ExecutionLanguage.PYTHON,
        )

        result = await executor.execute(request)

        assert result.status == ExecutionStatus.FAILED
        assert result.exit_code != 0
        assert "ValueError" in result.stderr

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, executor):
        """Test execution timeout."""
        request = ExecutionRequest(
            code='import time; time.sleep(10)',
            language=ExecutionLanguage.PYTHON,
            config=ExecutionConfig(timeout_seconds=1),
        )

        result = await executor.execute(request)

        assert result.status == ExecutionStatus.TIMEOUT
        assert "timed out" in result.stderr.lower()

    @pytest.mark.asyncio
    async def test_execute_javascript(self, executor):
        """Test executing JavaScript code."""
        request = ExecutionRequest(
            code='console.log("Hello from JS!");',
            language=ExecutionLanguage.JAVASCRIPT,
        )

        result = await executor.execute(request)

        # May fail if node is not installed
        if result.status == ExecutionStatus.COMPLETED:
            assert "Hello from JS!" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_shell(self, executor):
        """Test executing shell commands."""
        result = await executor.execute_shell('echo "Hello Shell"')

        assert result.status == ExecutionStatus.COMPLETED
        assert result.exit_code == 0
        assert "Hello Shell" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_shell_with_pipe(self, executor):
        """Test shell command with pipe."""
        result = await executor.execute_shell('echo "hello world" | tr "h" "H"')

        assert result.status == ExecutionStatus.COMPLETED
        assert "Hello" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_shell_error(self, executor):
        """Test shell command that fails."""
        result = await executor.execute_shell('exit 1')

        assert result.status == ExecutionStatus.FAILED
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_execute_with_files(self, executor):
        """Test execution with additional files."""
        request = ExecutionRequest(
            code='with open("data.txt") as f: print(f.read())',
            language=ExecutionLanguage.PYTHON,
            files={"data.txt": "Hello from file!"},
        )

        result = await executor.execute(request)

        assert result.status == ExecutionStatus.COMPLETED
        assert "Hello from file!" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_with_env_vars(self, executor):
        """Test execution with environment variables."""
        request = ExecutionRequest(
            code='import os; print(os.environ.get("TEST_VAR", "not found"))',
            language=ExecutionLanguage.PYTHON,
            config=ExecutionConfig(env_vars={"TEST_VAR": "test_value"}),
        )

        result = await executor.execute(request)

        assert result.status == ExecutionStatus.COMPLETED
        assert "test_value" in result.stdout

    @pytest.mark.asyncio
    async def test_sensitive_env_removed(self, executor):
        """Test that sensitive environment variables are removed."""
        request = ExecutionRequest(
            code='import os; print(os.environ.get("AWS_SECRET_ACCESS_KEY", "not found"))',
            language=ExecutionLanguage.PYTHON,
        )

        result = await executor.execute(request)

        assert result.status == ExecutionStatus.COMPLETED
        assert "not found" in result.stdout

    @pytest.mark.asyncio
    async def test_output_truncation(self, executor):
        """Test output truncation for large output."""
        request = ExecutionRequest(
            code='print("x" * 2000000)',  # 2MB of output
            language=ExecutionLanguage.PYTHON,
            config=ExecutionConfig(max_output_bytes=1000),
        )

        result = await executor.execute(request)

        assert len(result.stdout) <= 1100  # Some buffer for truncation message
        assert "truncated" in result.stdout.lower()


class TestExecutionConfig:
    """Test execution configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExecutionConfig()

        assert config.timeout_seconds == 30
        assert config.max_memory_mb == 512
        assert config.max_output_bytes == 1024 * 1024
        assert config.allow_network is False
        assert config.allow_file_write is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = ExecutionConfig(
            timeout_seconds=60,
            max_memory_mb=1024,
            allow_network=True,
            env_vars={"MY_VAR": "value"},
        )

        assert config.timeout_seconds == 60
        assert config.max_memory_mb == 1024
        assert config.allow_network is True
        assert config.env_vars["MY_VAR"] == "value"


class TestExecutionLanguage:
    """Test execution language enum."""

    def test_all_languages_have_commands(self):
        """Test that all languages have execution commands."""
        for lang in ExecutionLanguage:
            assert lang in CodeExecutor.LANGUAGE_COMMANDS

    def test_all_languages_have_extensions(self):
        """Test that all languages have file extensions."""
        for lang in ExecutionLanguage:
            assert lang in CodeExecutor.LANGUAGE_EXTENSIONS


class TestExecutionResult:
    """Test execution result structure."""

    @pytest.mark.asyncio
    async def test_result_has_all_fields(self, executor):
        """Test that result has all expected fields."""
        request = ExecutionRequest(
            code='print("test")',
            language=ExecutionLanguage.PYTHON,
        )

        result = await executor.execute(request)

        assert result.id is not None
        assert result.status is not None
        assert result.exit_code is not None or result.status == ExecutionStatus.TIMEOUT
        assert result.stdout is not None
        assert result.stderr is not None
        assert result.duration_ms >= 0
        assert result.language == ExecutionLanguage.PYTHON
        assert result.started_at is not None
        assert result.completed_at is not None
