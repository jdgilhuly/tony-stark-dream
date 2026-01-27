"""
Tool Definitions for Claude

Defines the tools that Claude can use, including file operations,
code execution, web browsing, and more.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from .claude_client import ToolDefinition

logger = logging.getLogger(__name__)


# Service base URLs (configurable)
CODE_SERVICE_URL = "http://localhost:8010"
BROWSER_SERVICE_URL = "http://localhost:8012"
MEMORY_SERVICE_URL = "http://localhost:8011"


def get_file_tools() -> List[ToolDefinition]:
    """Get file operation tools."""

    async def read_file(path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
        """Read a file's contents."""
        async with httpx.AsyncClient() as client:
            params = {"path": path}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit
            response = await client.get(f"{CODE_SERVICE_URL}/file", params=params)
            if response.status_code == 200:
                return response.json()["content"]
            return f"Error: {response.text}"

    async def write_file(path: str, content: str) -> str:
        """Write content to a file."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CODE_SERVICE_URL}/file",
                json={"path": path, "content": content}
            )
            return "File written successfully" if response.status_code == 200 else f"Error: {response.text}"

    async def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        """Edit a file by replacing text."""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{CODE_SERVICE_URL}/file",
                json={
                    "path": path,
                    "old_string": old_string,
                    "new_string": new_string,
                    "replace_all": replace_all,
                }
            )
            return "File edited successfully" if response.status_code == 200 else f"Error: {response.text}"

    async def list_files(path: str, recursive: bool = False) -> str:
        """List files in a directory."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CODE_SERVICE_URL}/files",
                params={"path": path, "recursive": recursive}
            )
            if response.status_code == 200:
                files = response.json()["files"]
                return "\n".join(files)
            return f"Error: {response.text}"

    async def search_files(path: str, pattern: str, file_pattern: Optional[str] = None) -> str:
        """Search for text in files."""
        async with httpx.AsyncClient() as client:
            params = {"path": path, "pattern": pattern}
            if file_pattern:
                params["file_pattern"] = file_pattern
            response = await client.get(f"{CODE_SERVICE_URL}/search", params=params)
            if response.status_code == 200:
                results = response.json()["results"]
                output = []
                for r in results:
                    output.append(f"{r['file']}:{r['line']}: {r['content']}")
                return "\n".join(output) or "No matches found"
            return f"Error: {response.text}"

    async def glob_files(path: str, pattern: str) -> str:
        """Find files matching a glob pattern."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CODE_SERVICE_URL}/glob",
                params={"path": path, "pattern": pattern}
            )
            if response.status_code == 200:
                files = response.json()["files"]
                return "\n".join(files) or "No files found"
            return f"Error: {response.text}"

    return [
        ToolDefinition(
            name="read_file",
            description="Read the contents of a file at the specified path. Returns the file content as text.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute path to the file to read"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start reading from (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (optional)"
                    }
                },
                "required": ["path"]
            },
            handler=read_file,
        ),
        ToolDefinition(
            name="write_file",
            description="Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["path", "content"]
            },
            handler=write_file,
        ),
        ToolDefinition(
            name="edit_file",
            description="Edit a file by replacing occurrences of old_string with new_string.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The absolute path to the file to edit"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The text to find and replace"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The replacement text"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace all occurrences (default: false)"
                    }
                },
                "required": ["path", "old_string", "new_string"]
            },
            handler=edit_file,
        ),
        ToolDefinition(
            name="list_files",
            description="List files and directories in the specified path.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory path to list"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List files recursively (default: false)"
                    }
                },
                "required": ["path"]
            },
            handler=list_files,
        ),
        ToolDefinition(
            name="search_files",
            description="Search for a regex pattern in files. Returns matching lines with file and line numbers.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The directory to search in"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "The regex pattern to search for"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g., '*.py')"
                    }
                },
                "required": ["path", "pattern"]
            },
            handler=search_files,
        ),
        ToolDefinition(
            name="glob_files",
            description="Find files matching a glob pattern.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The base directory to search from"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "The glob pattern (e.g., '**/*.py')"
                    }
                },
                "required": ["path", "pattern"]
            },
            handler=glob_files,
        ),
    ]


def get_git_tools() -> List[ToolDefinition]:
    """Get git operation tools."""

    async def git_status(repo_path: str) -> str:
        """Get git status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CODE_SERVICE_URL}/git/status",
                params={"repo_path": repo_path}
            )
            if response.status_code == 200:
                data = response.json()
                output = [f"Branch: {data['branch']}"]
                if data.get("staged"):
                    output.append(f"Staged: {', '.join(data['staged'])}")
                if data.get("modified"):
                    output.append(f"Modified: {', '.join(data['modified'])}")
                if data.get("untracked"):
                    output.append(f"Untracked: {', '.join(data['untracked'])}")
                return "\n".join(output)
            return f"Error: {response.text}"

    async def git_diff(repo_path: str, staged: bool = False, file: Optional[str] = None) -> str:
        """Get git diff."""
        async with httpx.AsyncClient() as client:
            params = {"repo_path": repo_path, "staged": staged}
            if file:
                params["file"] = file
            response = await client.get(f"{CODE_SERVICE_URL}/git/diff", params=params)
            if response.status_code == 200:
                return response.json()["diff"]
            return f"Error: {response.text}"

    async def git_commit(repo_path: str, message: str, files: Optional[List[str]] = None) -> str:
        """Create a git commit."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CODE_SERVICE_URL}/git/commit",
                json={
                    "repo_path": repo_path,
                    "message": message,
                    "files": files,
                }
            )
            if response.status_code == 200:
                data = response.json()
                return f"Committed: {data['commit_hash']}"
            return f"Error: {response.text}"

    async def git_log(repo_path: str, max_count: int = 10) -> str:
        """Get git log."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CODE_SERVICE_URL}/git/log",
                params={"repo_path": repo_path, "max_count": max_count}
            )
            if response.status_code == 200:
                commits = response.json()["commits"]
                output = []
                for c in commits:
                    output.append(f"{c['hash'][:7]} - {c['message']} ({c['author']})")
                return "\n".join(output)
            return f"Error: {response.text}"

    return [
        ToolDefinition(
            name="git_status",
            description="Get the current git status of a repository.",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the git repository"
                    }
                },
                "required": ["repo_path"]
            },
            handler=git_status,
        ),
        ToolDefinition(
            name="git_diff",
            description="Get the git diff showing changes.",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the git repository"
                    },
                    "staged": {
                        "type": "boolean",
                        "description": "Show only staged changes (default: false)"
                    },
                    "file": {
                        "type": "string",
                        "description": "Specific file to diff (optional)"
                    }
                },
                "required": ["repo_path"]
            },
            handler=git_diff,
        ),
        ToolDefinition(
            name="git_commit",
            description="Create a git commit with the specified message.",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the git repository"
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific files to commit (optional, stages all if not specified)"
                    }
                },
                "required": ["repo_path", "message"]
            },
            handler=git_commit,
        ),
        ToolDefinition(
            name="git_log",
            description="Get the git commit log.",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Path to the git repository"
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "Maximum number of commits to return (default: 10)"
                    }
                },
                "required": ["repo_path"]
            },
            handler=git_log,
        ),
    ]


def get_execution_tools() -> List[ToolDefinition]:
    """Get code execution tools."""

    async def run_code(
        code: str,
        language: str = "python",
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None,
    ) -> str:
        """Execute code in a sandboxed environment."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CODE_SERVICE_URL}/execute",
                json={
                    "code": code,
                    "language": language,
                    "timeout": timeout,
                    "env": env or {},
                },
                timeout=timeout + 10,
            )
            if response.status_code == 200:
                data = response.json()
                output = []
                if data.get("stdout"):
                    output.append(f"stdout:\n{data['stdout']}")
                if data.get("stderr"):
                    output.append(f"stderr:\n{data['stderr']}")
                output.append(f"exit_code: {data.get('exit_code', 0)}")
                return "\n".join(output)
            return f"Error: {response.text}"

    async def run_bash(command: str, working_dir: Optional[str] = None, timeout: int = 30) -> str:
        """Execute a bash command."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CODE_SERVICE_URL}/execute",
                json={
                    "code": command,
                    "language": "bash",
                    "working_dir": working_dir,
                    "timeout": timeout,
                },
                timeout=timeout + 10,
            )
            if response.status_code == 200:
                data = response.json()
                output = []
                if data.get("stdout"):
                    output.append(data["stdout"])
                if data.get("stderr"):
                    output.append(f"stderr: {data['stderr']}")
                return "\n".join(output) or "(no output)"
            return f"Error: {response.text}"

    return [
        ToolDefinition(
            name="run_code",
            description="Execute code in a sandboxed environment. Supports Python, JavaScript, TypeScript, and shell scripts.",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The code to execute"
                    },
                    "language": {
                        "type": "string",
                        "enum": ["python", "javascript", "typescript", "bash", "shell"],
                        "description": "Programming language (default: python)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Execution timeout in seconds (default: 30)"
                    },
                    "env": {
                        "type": "object",
                        "description": "Environment variables to set"
                    }
                },
                "required": ["code"]
            },
            handler=run_code,
        ),
        ToolDefinition(
            name="run_bash",
            description="Execute a bash command in the terminal.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory for the command (optional)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Execution timeout in seconds (default: 30)"
                    }
                },
                "required": ["command"]
            },
            handler=run_bash,
        ),
    ]


def get_browser_tools() -> List[ToolDefinition]:
    """Get browser automation tools."""

    async def browse_url(url: str, extract_text: bool = True) -> str:
        """Browse a URL and extract content."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BROWSER_SERVICE_URL}/scrape",
                params={
                    "url": url,
                    "include_html": False,
                    "screenshot": False,
                },
                timeout=60.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("markdown") or data.get("text", "")
            return f"Error: {response.text}"

    async def web_search(query: str) -> str:
        """Search the web (via DuckDuckGo)."""
        # Simple DuckDuckGo instant answer API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_redirect": 1,
                    "no_html": 1,
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                results = []

                # Abstract
                if data.get("Abstract"):
                    results.append(f"Summary: {data['Abstract']}")
                    if data.get("AbstractURL"):
                        results.append(f"Source: {data['AbstractURL']}")

                # Related topics
                for topic in data.get("RelatedTopics", [])[:5]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append(f"- {topic['Text']}")

                return "\n".join(results) if results else "No results found"
            return f"Error: {response.text}"

    return [
        ToolDefinition(
            name="browse_url",
            description="Browse a URL and extract its content as markdown text.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to browse"
                    },
                    "extract_text": {
                        "type": "boolean",
                        "description": "Extract text content (default: true)"
                    }
                },
                "required": ["url"]
            },
            handler=browse_url,
        ),
        ToolDefinition(
            name="web_search",
            description="Search the web for information.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            },
            handler=web_search,
        ),
    ]


def get_memory_tools() -> List[ToolDefinition]:
    """Get memory/knowledge tools."""

    async def remember(content: str, memory_type: str = "fact", importance: float = 0.6) -> str:
        """Store something in memory."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMORY_SERVICE_URL}/memory",
                json={
                    "content": content,
                    "memory_type": memory_type,
                    "importance": importance,
                }
            )
            if response.status_code == 200:
                return f"Remembered: {content[:50]}..."
            return f"Error: {response.text}"

    async def recall(query: str, max_results: int = 5) -> str:
        """Search memory for relevant information."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMORY_SERVICE_URL}/memory/search",
                json={
                    "query": query,
                    "max_results": max_results,
                }
            )
            if response.status_code == 200:
                results = response.json()
                output = []
                for r in results:
                    memory = r["memory"]
                    output.append(f"- {memory['content']} (relevance: {r['relevance_score']:.2f})")
                return "\n".join(output) if output else "No relevant memories found"
            return f"Error: {response.text}"

    return [
        ToolDefinition(
            name="remember",
            description="Store information in long-term memory for future reference.",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The information to remember"
                    },
                    "memory_type": {
                        "type": "string",
                        "enum": ["fact", "preference", "instruction", "event", "entity"],
                        "description": "Type of memory (default: fact)"
                    },
                    "importance": {
                        "type": "number",
                        "description": "Importance score 0-1 (default: 0.6)"
                    }
                },
                "required": ["content"]
            },
            handler=remember,
        ),
        ToolDefinition(
            name="recall",
            description="Search memory for relevant information based on a query.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in memory"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 5)"
                    }
                },
                "required": ["query"]
            },
            handler=recall,
        ),
    ]


def get_all_tools() -> List[ToolDefinition]:
    """Get all available tools."""
    tools = []
    tools.extend(get_file_tools())
    tools.extend(get_git_tools())
    tools.extend(get_execution_tools())
    tools.extend(get_browser_tools())
    tools.extend(get_memory_tools())
    return tools
