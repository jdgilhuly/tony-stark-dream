"""
Sandboxed Code Execution Module

Provides secure code execution in isolated environments.
Supports Python, JavaScript, Shell, and more.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ExecutionLanguage(str, Enum):
    """Supported execution languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    SHELL = "shell"
    BASH = "bash"
    ZSH = "zsh"


class ExecutionStatus(str, Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ExecutionConfig:
    """Configuration for code execution."""
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_output_bytes: int = 1024 * 1024  # 1MB
    allow_network: bool = False
    allow_file_write: bool = True
    working_dir: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of code execution."""
    id: str
    status: ExecutionStatus
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int
    language: ExecutionLanguage
    started_at: str
    completed_at: Optional[str]
    error_message: Optional[str] = None


@dataclass
class ExecutionRequest:
    """Request to execute code."""
    code: str
    language: ExecutionLanguage
    config: ExecutionConfig = field(default_factory=ExecutionConfig)
    files: Dict[str, str] = field(default_factory=dict)  # filename -> content


class CodeExecutor:
    """
    Sandboxed code executor.

    Executes code in isolated temporary directories with
    resource limits and security restrictions.
    """

    # Language to command mapping
    LANGUAGE_COMMANDS = {
        ExecutionLanguage.PYTHON: ["python3", "-u"],
        ExecutionLanguage.JAVASCRIPT: ["node"],
        ExecutionLanguage.TYPESCRIPT: ["npx", "ts-node"],
        ExecutionLanguage.SHELL: ["sh"],
        ExecutionLanguage.BASH: ["bash"],
        ExecutionLanguage.ZSH: ["zsh"],
    }

    # Language to file extension mapping
    LANGUAGE_EXTENSIONS = {
        ExecutionLanguage.PYTHON: ".py",
        ExecutionLanguage.JAVASCRIPT: ".js",
        ExecutionLanguage.TYPESCRIPT: ".ts",
        ExecutionLanguage.SHELL: ".sh",
        ExecutionLanguage.BASH: ".sh",
        ExecutionLanguage.ZSH: ".zsh",
    }

    def __init__(self, sandbox_root: Optional[str] = None):
        self.sandbox_root = Path(sandbox_root) if sandbox_root else Path(tempfile.gettempdir()) / "jarvis_sandbox"
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        self._running_processes: Dict[str, subprocess.Popen] = {}

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute code in a sandboxed environment.

        Args:
            request: Execution request with code and config

        Returns:
            ExecutionResult with output and status
        """
        execution_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow()

        # Create isolated workspace
        workspace = self.sandbox_root / execution_id
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            # Write code to file
            extension = self.LANGUAGE_EXTENSIONS.get(request.language, ".txt")
            code_file = workspace / f"main{extension}"
            code_file.write_text(request.code)

            # Write additional files
            for filename, content in request.files.items():
                file_path = workspace / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Build command
            command = self._build_command(request.language, code_file)

            # Set up environment
            env = self._build_environment(request.config)

            # Execute with timeout
            result = await self._run_process(
                command=command,
                cwd=str(workspace),
                env=env,
                timeout=request.config.timeout_seconds,
                max_output=request.config.max_output_bytes,
                execution_id=execution_id,
            )

            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            return ExecutionResult(
                id=execution_id,
                status=ExecutionStatus.COMPLETED if result["exit_code"] == 0 else ExecutionStatus.FAILED,
                exit_code=result["exit_code"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                duration_ms=duration_ms,
                language=request.language,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                error_message=result.get("error"),
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                id=execution_id,
                status=ExecutionStatus.TIMEOUT,
                exit_code=None,
                stdout="",
                stderr=f"Execution timed out after {request.config.timeout_seconds} seconds",
                duration_ms=request.config.timeout_seconds * 1000,
                language=request.language,
                started_at=started_at.isoformat(),
                completed_at=datetime.utcnow().isoformat(),
                error_message="Timeout",
            )

        except Exception as e:
            logger.error(f"Execution error: {e}")
            return ExecutionResult(
                id=execution_id,
                status=ExecutionStatus.FAILED,
                exit_code=None,
                stdout="",
                stderr=str(e),
                duration_ms=0,
                language=request.language,
                started_at=started_at.isoformat(),
                completed_at=datetime.utcnow().isoformat(),
                error_message=str(e),
            )

        finally:
            # Cleanup workspace
            try:
                shutil.rmtree(workspace)
            except Exception as e:
                logger.warning(f"Failed to cleanup workspace: {e}")

            # Remove from running processes
            self._running_processes.pop(execution_id, None)

    async def execute_shell(
        self,
        command: str,
        config: Optional[ExecutionConfig] = None,
        working_dir: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute a shell command.

        Args:
            command: Shell command to execute
            config: Execution configuration
            working_dir: Working directory

        Returns:
            ExecutionResult with output and status
        """
        config = config or ExecutionConfig()
        execution_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow()

        try:
            env = self._build_environment(config)
            cwd = working_dir or config.working_dir or str(Path.cwd())

            result = await self._run_process(
                command=["bash", "-c", command],
                cwd=cwd,
                env=env,
                timeout=config.timeout_seconds,
                max_output=config.max_output_bytes,
                execution_id=execution_id,
            )

            completed_at = datetime.utcnow()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            return ExecutionResult(
                id=execution_id,
                status=ExecutionStatus.COMPLETED if result["exit_code"] == 0 else ExecutionStatus.FAILED,
                exit_code=result["exit_code"],
                stdout=result["stdout"],
                stderr=result["stderr"],
                duration_ms=duration_ms,
                language=ExecutionLanguage.SHELL,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                error_message=result.get("error"),
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                id=execution_id,
                status=ExecutionStatus.TIMEOUT,
                exit_code=None,
                stdout="",
                stderr=f"Command timed out after {config.timeout_seconds} seconds",
                duration_ms=config.timeout_seconds * 1000,
                language=ExecutionLanguage.SHELL,
                started_at=started_at.isoformat(),
                completed_at=datetime.utcnow().isoformat(),
                error_message="Timeout",
            )

        except Exception as e:
            return ExecutionResult(
                id=execution_id,
                status=ExecutionStatus.FAILED,
                exit_code=None,
                stdout="",
                stderr=str(e),
                duration_ms=0,
                language=ExecutionLanguage.SHELL,
                started_at=started_at.isoformat(),
                completed_at=datetime.utcnow().isoformat(),
                error_message=str(e),
            )

    async def cancel(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        process = self._running_processes.get(execution_id)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return True
        return False

    def _build_command(self, language: ExecutionLanguage, code_file: Path) -> List[str]:
        """Build the execution command."""
        base_command = self.LANGUAGE_COMMANDS.get(language, ["python3"])
        return base_command + [str(code_file)]

    def _build_environment(self, config: ExecutionConfig) -> Dict[str, str]:
        """Build environment variables for execution."""
        env = os.environ.copy()

        # Add user-specified environment variables
        env.update(config.env_vars)

        # Security: Remove sensitive environment variables
        sensitive_vars = [
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
            "GITHUB_TOKEN", "OPENAI_API_KEY",
            "DATABASE_URL", "REDIS_URL",
        ]
        for var in sensitive_vars:
            env.pop(var, None)

        return env

    async def _run_process(
        self,
        command: List[str],
        cwd: str,
        env: Dict[str, str],
        timeout: int,
        max_output: int,
        execution_id: str,
    ) -> Dict[str, Any]:
        """Run a process with timeout and output limits."""

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Track the process
        # Note: asyncio subprocess doesn't have same interface as subprocess.Popen
        # so we can't easily track it the same way

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            # Truncate output if needed
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            if len(stdout_str) > max_output:
                stdout_str = stdout_str[:max_output] + f"\n... (truncated, {len(stdout_str) - max_output} bytes omitted)"
            if len(stderr_str) > max_output:
                stderr_str = stderr_str[:max_output] + f"\n... (truncated, {len(stderr_str) - max_output} bytes omitted)"

            return {
                "exit_code": process.returncode,
                "stdout": stdout_str,
                "stderr": stderr_str,
            }

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise


class DockerExecutor:
    """
    Docker-based code executor for maximum isolation.

    Executes code in Docker containers with resource limits.
    """

    # Language to Docker image mapping
    LANGUAGE_IMAGES = {
        ExecutionLanguage.PYTHON: "python:3.11-slim",
        ExecutionLanguage.JAVASCRIPT: "node:20-slim",
        ExecutionLanguage.TYPESCRIPT: "node:20-slim",
        ExecutionLanguage.SHELL: "alpine:latest",
        ExecutionLanguage.BASH: "bash:latest",
    }

    def __init__(self):
        self._check_docker()

    def _check_docker(self):
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Docker is not running")
        except FileNotFoundError:
            raise RuntimeError("Docker is not installed")

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute code in a Docker container."""
        execution_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow()

        # Get Docker image
        image = self.LANGUAGE_IMAGES.get(request.language, "python:3.11-slim")

        # Create temp directory for code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write code file
            extension = CodeExecutor.LANGUAGE_EXTENSIONS.get(request.language, ".txt")
            code_file = Path(tmpdir) / f"main{extension}"
            code_file.write_text(request.code)

            # Write additional files
            for filename, content in request.files.items():
                file_path = Path(tmpdir) / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Build Docker command
            docker_cmd = [
                "docker", "run",
                "--rm",
                "--memory", f"{request.config.max_memory_mb}m",
                "--cpus", "1",
                "--network", "none" if not request.config.allow_network else "bridge",
                "-v", f"{tmpdir}:/code:ro",
                "-w", "/code",
                image,
            ]

            # Add language-specific command
            lang_cmd = CodeExecutor.LANGUAGE_COMMANDS.get(request.language, ["python3"])
            docker_cmd.extend(lang_cmd)
            docker_cmd.append(f"main{extension}")

            try:
                process = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=request.config.timeout_seconds
                )

                completed_at = datetime.utcnow()
                duration_ms = int((completed_at - started_at).total_seconds() * 1000)

                return ExecutionResult(
                    id=execution_id,
                    status=ExecutionStatus.COMPLETED if process.returncode == 0 else ExecutionStatus.FAILED,
                    exit_code=process.returncode,
                    stdout=stdout.decode('utf-8', errors='replace'),
                    stderr=stderr.decode('utf-8', errors='replace'),
                    duration_ms=duration_ms,
                    language=request.language,
                    started_at=started_at.isoformat(),
                    completed_at=completed_at.isoformat(),
                )

            except asyncio.TimeoutError:
                # Kill the container
                subprocess.run(
                    ["docker", "kill", execution_id],
                    capture_output=True
                )

                return ExecutionResult(
                    id=execution_id,
                    status=ExecutionStatus.TIMEOUT,
                    exit_code=None,
                    stdout="",
                    stderr=f"Execution timed out after {request.config.timeout_seconds} seconds",
                    duration_ms=request.config.timeout_seconds * 1000,
                    language=request.language,
                    started_at=started_at.isoformat(),
                    completed_at=datetime.utcnow().isoformat(),
                    error_message="Timeout",
                )

            except Exception as e:
                return ExecutionResult(
                    id=execution_id,
                    status=ExecutionStatus.FAILED,
                    exit_code=None,
                    stdout="",
                    stderr=str(e),
                    duration_ms=0,
                    language=request.language,
                    started_at=started_at.isoformat(),
                    completed_at=datetime.utcnow().isoformat(),
                    error_message=str(e),
                )


# Singleton executors
_code_executor: Optional[CodeExecutor] = None
_docker_executor: Optional[DockerExecutor] = None


def get_code_executor() -> CodeExecutor:
    """Get or create the code executor singleton."""
    global _code_executor
    if _code_executor is None:
        _code_executor = CodeExecutor()
    return _code_executor


def get_docker_executor() -> Optional[DockerExecutor]:
    """Get or create the Docker executor singleton."""
    global _docker_executor
    if _docker_executor is None:
        try:
            _docker_executor = DockerExecutor()
        except RuntimeError as e:
            logger.warning(f"Docker executor not available: {e}")
            return None
    return _docker_executor
