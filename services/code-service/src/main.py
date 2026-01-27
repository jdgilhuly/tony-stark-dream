"""
JARVIS Code Service - Main FastAPI Application

Provides Claude Code-like capabilities: file operations, git, code search.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .file_ops import FileOperations, FileInfo, FileContent, SearchMatch
from .git_ops import GitOperations, GitStatus, CommitInfo, FileDiff, BranchInfo
from .execution import (
    CodeExecutor, DockerExecutor,
    ExecutionRequest, ExecutionConfig, ExecutionResult,
    ExecutionLanguage, ExecutionStatus,
    get_code_executor, get_docker_executor,
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
    title="JARVIS Code Service",
    description="File operations, git management, and code intelligence",
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

# Initialize operations
file_ops = FileOperations(
    workspace_root=settings.workspace_root or None,
    max_file_size=settings.max_file_size_bytes,
)
git_ops = GitOperations(
    repo_path=settings.workspace_root or None,
    author_name=settings.git_author_name,
    author_email=settings.git_author_email,
)


# Request/Response Models
class ReadFileRequest(BaseModel):
    path: str
    offset: int = 0
    limit: Optional[int] = None


class WriteFileRequest(BaseModel):
    path: str
    content: str
    create_dirs: bool = True


class EditFileRequest(BaseModel):
    path: str
    old_text: str
    new_text: str
    replace_all: bool = False


class SearchRequest(BaseModel):
    pattern: str
    path: str = "."
    file_pattern: str = "*"
    case_sensitive: bool = True
    max_results: int = 100


class GlobRequest(BaseModel):
    pattern: str
    path: str = "."


class GitAddRequest(BaseModel):
    paths: List[str]


class GitCommitRequest(BaseModel):
    message: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None


class GitPushRequest(BaseModel):
    remote: str = "origin"
    branch: Optional[str] = None
    set_upstream: bool = False
    force: bool = False


class GitPullRequest(BaseModel):
    remote: str = "origin"
    branch: Optional[str] = None
    rebase: bool = False


class GitBranchRequest(BaseModel):
    name: str
    checkout: bool = True


class FileInfoResponse(BaseModel):
    path: str
    name: str
    extension: str
    size_bytes: int
    is_binary: bool
    encoding: Optional[str]
    line_count: Optional[int]


class FileContentResponse(BaseModel):
    path: str
    content: str
    encoding: str
    line_count: int


class SearchMatchResponse(BaseModel):
    path: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int


class EditResultResponse(BaseModel):
    path: str
    replacements: int
    content: str


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
        return {"user_id": payload.get("userId")}
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "timestamp": datetime.utcnow().isoformat()
    }


# File Operations Endpoints
@app.post("/file/read", response_model=FileContentResponse)
async def read_file(
    request: ReadFileRequest,
    user: dict = Depends(get_current_user)
):
    """Read a file's content."""
    try:
        content = await file_ops.read_file(
            request.path,
            request.offset,
            request.limit
        )
        return FileContentResponse(
            path=content.path,
            content=content.content,
            encoding=content.encoding,
            line_count=content.line_count,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Read file error: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file")


@app.post("/file/write", response_model=FileInfoResponse)
async def write_file(
    request: WriteFileRequest,
    user: dict = Depends(get_current_user)
):
    """Write content to a file."""
    try:
        info = await file_ops.write_file(
            request.path,
            request.content,
            request.create_dirs
        )
        return FileInfoResponse(
            path=info.path,
            name=info.name,
            extension=info.extension,
            size_bytes=info.size_bytes,
            is_binary=info.is_binary,
            encoding=info.encoding,
            line_count=info.line_count,
        )
    except Exception as e:
        logger.error(f"Write file error: {e}")
        raise HTTPException(status_code=500, detail="Failed to write file")


@app.post("/file/edit", response_model=EditResultResponse)
async def edit_file(
    request: EditFileRequest,
    user: dict = Depends(get_current_user)
):
    """Edit a file by replacing text."""
    try:
        content, replacements = await file_ops.edit_file(
            request.path,
            request.old_text,
            request.new_text,
            request.replace_all
        )
        return EditResultResponse(
            path=content.path,
            replacements=replacements,
            content=content.content,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Edit file error: {e}")
        raise HTTPException(status_code=500, detail="Failed to edit file")


@app.delete("/file/{path:path}")
async def delete_file(
    path: str,
    user: dict = Depends(get_current_user)
):
    """Delete a file."""
    try:
        await file_ops.delete_file(path)
        return {"status": "deleted", "path": path}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Delete file error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")


@app.get("/file/info/{path:path}", response_model=FileInfoResponse)
async def get_file_info(
    path: str,
    user: dict = Depends(get_current_user)
):
    """Get information about a file."""
    try:
        info = await file_ops.get_file_info(path)
        return FileInfoResponse(
            path=info.path,
            name=info.name,
            extension=info.extension,
            size_bytes=info.size_bytes,
            is_binary=info.is_binary,
            encoding=info.encoding,
            line_count=info.line_count,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Get file info error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file info")


@app.get("/file/list", response_model=List[FileInfoResponse])
async def list_files(
    path: str = ".",
    pattern: str = "*",
    recursive: bool = False,
    include_hidden: bool = False,
    user: dict = Depends(get_current_user)
):
    """List files in a directory."""
    try:
        files = await file_ops.list_files(path, pattern, recursive, include_hidden)
        return [
            FileInfoResponse(
                path=f.path,
                name=f.name,
                extension=f.extension,
                size_bytes=f.size_bytes,
                is_binary=f.is_binary,
                encoding=f.encoding,
                line_count=f.line_count,
            )
            for f in files
        ]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"List files error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files")


@app.post("/file/search", response_model=List[SearchMatchResponse])
async def search_files(
    request: SearchRequest,
    user: dict = Depends(get_current_user)
):
    """Search for a pattern in files."""
    try:
        matches = await file_ops.search_files(
            request.pattern,
            request.path,
            request.file_pattern,
            request.case_sensitive,
            request.max_results
        )
        return [
            SearchMatchResponse(
                path=m.path,
                line_number=m.line_number,
                line_content=m.line_content,
                match_start=m.match_start,
                match_end=m.match_end,
            )
            for m in matches
        ]
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@app.post("/file/glob", response_model=List[str])
async def glob_files(
    request: GlobRequest,
    user: dict = Depends(get_current_user)
):
    """Find files matching a glob pattern."""
    try:
        return await file_ops.glob_files(request.pattern, request.path)
    except Exception as e:
        logger.error(f"Glob error: {e}")
        raise HTTPException(status_code=500, detail="Glob failed")


# Git Operations Endpoints
@app.get("/git/status")
async def git_status(user: dict = Depends(get_current_user)):
    """Get git repository status."""
    try:
        status = git_ops.get_status()
        return {
            "branch": status.branch,
            "ahead": status.ahead,
            "behind": status.behind,
            "is_clean": status.is_clean,
            "staged": [
                {"path": f.path, "status": f.status.value, "old_path": f.old_path}
                for f in status.staged
            ],
            "unstaged": [
                {"path": f.path, "status": f.status.value}
                for f in status.unstaged
            ],
            "untracked": status.untracked,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Git status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get git status")


@app.get("/git/diff")
async def git_diff(
    staged: bool = False,
    path: Optional[str] = None,
    commit: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get diff of changes."""
    try:
        diffs = git_ops.get_diff(staged, path, commit)
        return [
            {
                "path": d.path,
                "old_path": d.old_path,
                "status": d.status.value,
                "additions": d.additions,
                "deletions": d.deletions,
                "hunks": [
                    {"content": h.content}
                    for h in d.hunks
                ],
            }
            for d in diffs
        ]
    except Exception as e:
        logger.error(f"Git diff error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get diff")


@app.post("/git/add")
async def git_add(
    request: GitAddRequest,
    user: dict = Depends(get_current_user)
):
    """Stage files for commit."""
    try:
        staged = git_ops.add_files(request.paths)
        return {"staged": staged}
    except Exception as e:
        logger.error(f"Git add error: {e}")
        raise HTTPException(status_code=500, detail="Failed to stage files")


@app.post("/git/add-all")
async def git_add_all(user: dict = Depends(get_current_user)):
    """Stage all changes."""
    try:
        staged = git_ops.add_all()
        return {"staged": staged}
    except Exception as e:
        logger.error(f"Git add all error: {e}")
        raise HTTPException(status_code=500, detail="Failed to stage all files")


@app.post("/git/reset")
async def git_reset(
    request: GitAddRequest,
    user: dict = Depends(get_current_user)
):
    """Unstage files."""
    try:
        unstaged = git_ops.reset_files(request.paths)
        return {"unstaged": unstaged}
    except Exception as e:
        logger.error(f"Git reset error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unstage files")


@app.post("/git/commit")
async def git_commit(
    request: GitCommitRequest,
    user: dict = Depends(get_current_user)
):
    """Create a commit."""
    try:
        commit = git_ops.commit(
            request.message,
            request.author_name,
            request.author_email
        )
        return {
            "sha": commit.sha,
            "short_sha": commit.short_sha,
            "message": commit.message,
            "author": commit.author,
            "date": commit.date,
            "files_changed": commit.files_changed,
        }
    except Exception as e:
        logger.error(f"Git commit error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create commit")


@app.get("/git/log")
async def git_log(
    max_count: int = 10,
    path: Optional[str] = None,
    branch: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get commit log."""
    try:
        commits = git_ops.get_log(max_count, path, branch)
        return [
            {
                "sha": c.sha,
                "short_sha": c.short_sha,
                "message": c.message,
                "author": c.author,
                "author_email": c.author_email,
                "date": c.date,
                "files_changed": c.files_changed,
            }
            for c in commits
        ]
    except Exception as e:
        logger.error(f"Git log error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get log")


@app.get("/git/branches")
async def git_branches(user: dict = Depends(get_current_user)):
    """Get list of branches."""
    try:
        branches = git_ops.get_branches()
        return [
            {
                "name": b.name,
                "is_current": b.is_current,
                "tracking": b.tracking,
                "ahead": b.ahead,
                "behind": b.behind,
                "last_commit": b.last_commit,
            }
            for b in branches
        ]
    except Exception as e:
        logger.error(f"Git branches error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get branches")


@app.post("/git/branch")
async def git_create_branch(
    request: GitBranchRequest,
    user: dict = Depends(get_current_user)
):
    """Create a new branch."""
    try:
        branch = git_ops.create_branch(request.name, request.checkout)
        return {
            "name": branch.name,
            "is_current": branch.is_current,
            "last_commit": branch.last_commit,
        }
    except Exception as e:
        logger.error(f"Git branch error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create branch")


@app.post("/git/checkout/{ref}")
async def git_checkout(
    ref: str,
    user: dict = Depends(get_current_user)
):
    """Checkout a branch or commit."""
    try:
        result = git_ops.checkout(ref)
        return {"checked_out": result}
    except Exception as e:
        logger.error(f"Git checkout error: {e}")
        raise HTTPException(status_code=500, detail="Failed to checkout")


@app.post("/git/push")
async def git_push(
    request: GitPushRequest,
    user: dict = Depends(get_current_user)
):
    """Push to remote."""
    try:
        success, message = git_ops.push(
            request.remote,
            request.branch,
            request.set_upstream,
            request.force
        )
        if success:
            return {"status": "success", "message": message}
        raise HTTPException(status_code=500, detail=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Git push error: {e}")
        raise HTTPException(status_code=500, detail="Failed to push")


@app.post("/git/pull")
async def git_pull(
    request: GitPullRequest,
    user: dict = Depends(get_current_user)
):
    """Pull from remote."""
    try:
        success, message = git_ops.pull(
            request.remote,
            request.branch,
            request.rebase
        )
        if success:
            return {"status": "success", "message": message}
        raise HTTPException(status_code=500, detail=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Git pull error: {e}")
        raise HTTPException(status_code=500, detail="Failed to pull")


@app.post("/git/stash")
async def git_stash(
    message: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Stash changes."""
    try:
        result = git_ops.stash(message)
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Git stash error: {e}")
        raise HTTPException(status_code=500, detail="Failed to stash")


@app.post("/git/stash-pop")
async def git_stash_pop(user: dict = Depends(get_current_user)):
    """Pop stashed changes."""
    try:
        result = git_ops.stash_pop()
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Git stash pop error: {e}")
        raise HTTPException(status_code=500, detail="Failed to pop stash")


# Code Execution Endpoints
class ExecuteCodeRequest(BaseModel):
    code: str
    language: str  # python, javascript, typescript, shell, bash
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    allow_network: bool = False
    env_vars: Dict[str, str] = {}
    files: Dict[str, str] = {}  # additional files


class ExecuteShellRequest(BaseModel):
    command: str
    working_dir: Optional[str] = None
    timeout_seconds: int = 30
    env_vars: Dict[str, str] = {}


class ExecutionResultResponse(BaseModel):
    id: str
    status: str
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_ms: int
    language: str
    started_at: str
    completed_at: Optional[str]
    error_message: Optional[str]


@app.post("/execute/code", response_model=ExecutionResultResponse)
async def execute_code(
    request: ExecuteCodeRequest,
    user: dict = Depends(get_current_user),
    use_docker: bool = False,
):
    """
    Execute code in a sandboxed environment.

    Supports: python, javascript, typescript, shell, bash, zsh
    """
    try:
        # Parse language
        try:
            language = ExecutionLanguage(request.language.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}. "
                       f"Supported: {[l.value for l in ExecutionLanguage]}"
            )

        # Build config
        config = ExecutionConfig(
            timeout_seconds=min(request.timeout_seconds, 300),  # Max 5 min
            max_memory_mb=min(request.max_memory_mb, 1024),  # Max 1GB
            allow_network=request.allow_network,
            env_vars=request.env_vars,
        )

        # Build request
        exec_request = ExecutionRequest(
            code=request.code,
            language=language,
            config=config,
            files=request.files,
        )

        # Get executor
        if use_docker:
            executor = get_docker_executor()
            if executor is None:
                raise HTTPException(
                    status_code=503,
                    detail="Docker executor not available"
                )
        else:
            executor = get_code_executor()

        # Execute
        result = await executor.execute(exec_request)

        logger.info(
            f"Code execution completed",
            extra={
                "user_id": user["user_id"],
                "language": language.value,
                "status": result.status.value,
                "duration_ms": result.duration_ms,
            }
        )

        return ExecutionResultResponse(
            id=result.id,
            status=result.status.value,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=result.duration_ms,
            language=result.language.value,
            started_at=result.started_at,
            completed_at=result.completed_at,
            error_message=result.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code execution error: {e}")
        raise HTTPException(status_code=500, detail="Code execution failed")


@app.post("/execute/shell", response_model=ExecutionResultResponse)
async def execute_shell(
    request: ExecuteShellRequest,
    user: dict = Depends(get_current_user),
):
    """Execute a shell command."""
    try:
        config = ExecutionConfig(
            timeout_seconds=min(request.timeout_seconds, 300),
            env_vars=request.env_vars,
            working_dir=request.working_dir,
        )

        executor = get_code_executor()
        result = await executor.execute_shell(
            request.command,
            config,
            request.working_dir,
        )

        logger.info(
            f"Shell execution completed",
            extra={
                "user_id": user["user_id"],
                "command": request.command[:50],
                "status": result.status.value,
                "duration_ms": result.duration_ms,
            }
        )

        return ExecutionResultResponse(
            id=result.id,
            status=result.status.value,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=result.duration_ms,
            language=result.language.value,
            started_at=result.started_at,
            completed_at=result.completed_at,
            error_message=result.error_message,
        )

    except Exception as e:
        logger.error(f"Shell execution error: {e}")
        raise HTTPException(status_code=500, detail="Shell execution failed")


@app.post("/execute/cancel/{execution_id}")
async def cancel_execution(
    execution_id: str,
    user: dict = Depends(get_current_user),
):
    """Cancel a running execution."""
    executor = get_code_executor()
    cancelled = await executor.cancel(execution_id)

    if cancelled:
        return {"status": "cancelled", "execution_id": execution_id}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Execution {execution_id} not found or already completed"
        )


@app.get("/execute/languages")
async def list_supported_languages():
    """List supported execution languages."""
    return {
        "languages": [
            {
                "id": lang.value,
                "name": lang.name,
                "extensions": [CodeExecutor.LANGUAGE_EXTENSIONS.get(lang, ".txt")],
            }
            for lang in ExecutionLanguage
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
