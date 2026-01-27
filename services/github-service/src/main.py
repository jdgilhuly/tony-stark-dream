"""
JARVIS GitHub Service - Main FastAPI Application

Provides GitHub integration for repository, issue, and PR management.
"""

import hashlib
import hmac
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError

from .config import get_settings
from .github_client import (
    get_github_client,
    RepoInfo,
    IssueInfo,
    PRInfo,
    CommitInfo,
    FileContent,
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
    get_github_client()
    yield
    logger.info(f"Shutting down {settings.service_name}")


app = FastAPI(
    title="JARVIS GitHub Service",
    description="GitHub integration for repository, issue, and PR management",
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
class RepoInfoModel(BaseModel):
    name: str
    full_name: str
    description: Optional[str]
    url: str
    clone_url: str
    ssh_url: str
    default_branch: str
    language: Optional[str]
    stars: int
    forks: int
    open_issues: int
    is_private: bool
    created_at: str
    updated_at: str
    topics: List[str] = []


class IssueInfoModel(BaseModel):
    number: int
    title: str
    body: Optional[str]
    state: str
    url: str
    user: str
    labels: List[str]
    assignees: List[str]
    created_at: str
    updated_at: str
    closed_at: Optional[str] = None
    comments: int = 0


class CreateIssueRequest(BaseModel):
    title: str
    body: Optional[str] = None
    labels: Optional[List[str]] = None
    assignees: Optional[List[str]] = None


class PRInfoModel(BaseModel):
    number: int
    title: str
    body: Optional[str]
    state: str
    url: str
    user: str
    head_branch: str
    base_branch: str
    labels: List[str]
    reviewers: List[str]
    created_at: str
    updated_at: str
    merged_at: Optional[str] = None
    closed_at: Optional[str] = None
    mergeable: Optional[bool] = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0


class CreatePRRequest(BaseModel):
    title: str
    head: str
    base: str
    body: Optional[str] = None
    draft: bool = False


class MergePRRequest(BaseModel):
    commit_message: Optional[str] = None
    merge_method: str = "merge"  # merge, squash, rebase


class CommitInfoModel(BaseModel):
    sha: str
    message: str
    author: str
    author_email: str
    date: str
    url: str
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0


class FileContentModel(BaseModel):
    path: str
    content: str
    sha: str
    size: int


class CreateFileRequest(BaseModel):
    path: str
    content: str
    message: str
    branch: Optional[str] = None


class UpdateFileRequest(BaseModel):
    path: str
    content: str
    message: str
    sha: str
    branch: Optional[str] = None


class CommentRequest(BaseModel):
    body: str


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
        "timestamp": datetime.utcnow().isoformat(),
    }


# Repository endpoints
@app.get("/repos/{owner}/{repo}", response_model=RepoInfoModel)
async def get_repo(
    owner: str,
    repo: str,
    user: dict = Depends(get_current_user),
):
    """Get repository information."""
    client = get_github_client()
    info = await client.get_repo(f"{owner}/{repo}")

    if not info:
        raise HTTPException(status_code=404, detail="Repository not found")

    return RepoInfoModel(**info.__dict__)


@app.get("/repos", response_model=List[RepoInfoModel])
async def list_repos(
    github_user: Optional[str] = None,
    type: str = "all",
    sort: str = "updated",
    limit: int = 30,
    user: dict = Depends(get_current_user),
):
    """List repositories."""
    client = get_github_client()
    repos = await client.list_repos(github_user, type, sort, limit)

    return [RepoInfoModel(**r.__dict__) for r in repos]


# Issue endpoints
@app.get("/repos/{owner}/{repo}/issues/{issue_number}", response_model=IssueInfoModel)
async def get_issue(
    owner: str,
    repo: str,
    issue_number: int,
    user: dict = Depends(get_current_user),
):
    """Get an issue by number."""
    client = get_github_client()
    info = await client.get_issue(f"{owner}/{repo}", issue_number)

    if not info:
        raise HTTPException(status_code=404, detail="Issue not found")

    return IssueInfoModel(**info.__dict__)


@app.get("/repos/{owner}/{repo}/issues", response_model=List[IssueInfoModel])
async def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 30,
    user: dict = Depends(get_current_user),
):
    """List issues in a repository."""
    client = get_github_client()
    label_list = labels.split(",") if labels else None
    issues = await client.list_issues(
        f"{owner}/{repo}", state, label_list, assignee, limit
    )

    return [IssueInfoModel(**i.__dict__) for i in issues]


@app.post("/repos/{owner}/{repo}/issues", response_model=IssueInfoModel)
async def create_issue(
    owner: str,
    repo: str,
    request: CreateIssueRequest,
    user: dict = Depends(get_current_user),
):
    """Create a new issue."""
    client = get_github_client()
    info = await client.create_issue(
        f"{owner}/{repo}",
        request.title,
        request.body,
        request.labels,
        request.assignees,
    )

    if not info:
        raise HTTPException(status_code=500, detail="Failed to create issue")

    return IssueInfoModel(**info.__dict__)


@app.put("/repos/{owner}/{repo}/issues/{issue_number}/close")
async def close_issue(
    owner: str,
    repo: str,
    issue_number: int,
    user: dict = Depends(get_current_user),
):
    """Close an issue."""
    client = get_github_client()
    success = await client.close_issue(f"{owner}/{repo}", issue_number)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to close issue")

    return {"status": "closed", "issue_number": issue_number}


@app.post("/repos/{owner}/{repo}/issues/{issue_number}/comments")
async def add_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    request: CommentRequest,
    user: dict = Depends(get_current_user),
):
    """Add a comment to an issue."""
    client = get_github_client()
    success = await client.add_issue_comment(
        f"{owner}/{repo}", issue_number, request.body
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to add comment")

    return {"status": "created"}


# PR endpoints
@app.get("/repos/{owner}/{repo}/pulls/{pr_number}", response_model=PRInfoModel)
async def get_pr(
    owner: str,
    repo: str,
    pr_number: int,
    user: dict = Depends(get_current_user),
):
    """Get a pull request by number."""
    client = get_github_client()
    info = await client.get_pr(f"{owner}/{repo}", pr_number)

    if not info:
        raise HTTPException(status_code=404, detail="Pull request not found")

    return PRInfoModel(**info.__dict__)


@app.get("/repos/{owner}/{repo}/pulls", response_model=List[PRInfoModel])
async def list_prs(
    owner: str,
    repo: str,
    state: str = "open",
    base: Optional[str] = None,
    head: Optional[str] = None,
    limit: int = 30,
    user: dict = Depends(get_current_user),
):
    """List pull requests in a repository."""
    client = get_github_client()
    prs = await client.list_prs(f"{owner}/{repo}", state, base, head, limit)

    return [PRInfoModel(**p.__dict__) for p in prs]


@app.post("/repos/{owner}/{repo}/pulls", response_model=PRInfoModel)
async def create_pr(
    owner: str,
    repo: str,
    request: CreatePRRequest,
    user: dict = Depends(get_current_user),
):
    """Create a pull request."""
    client = get_github_client()
    info = await client.create_pr(
        f"{owner}/{repo}",
        request.title,
        request.head,
        request.base,
        request.body,
        request.draft,
    )

    if not info:
        raise HTTPException(status_code=500, detail="Failed to create pull request")

    return PRInfoModel(**info.__dict__)


@app.put("/repos/{owner}/{repo}/pulls/{pr_number}/merge")
async def merge_pr(
    owner: str,
    repo: str,
    pr_number: int,
    request: MergePRRequest,
    user: dict = Depends(get_current_user),
):
    """Merge a pull request."""
    client = get_github_client()
    success = await client.merge_pr(
        f"{owner}/{repo}",
        pr_number,
        request.commit_message,
        request.merge_method,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to merge pull request")

    return {"status": "merged", "pr_number": pr_number}


# Commit endpoints
@app.get("/repos/{owner}/{repo}/commits", response_model=List[CommitInfoModel])
async def get_commits(
    owner: str,
    repo: str,
    branch: Optional[str] = None,
    limit: int = 30,
    user: dict = Depends(get_current_user),
):
    """Get commit history."""
    client = get_github_client()
    commits = await client.get_commits(f"{owner}/{repo}", branch, limit=limit)

    return [CommitInfoModel(**c.__dict__) for c in commits]


# File endpoints
@app.get("/repos/{owner}/{repo}/contents/{path:path}", response_model=FileContentModel)
async def get_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Get file content from repository."""
    client = get_github_client()
    content = await client.get_file_content(f"{owner}/{repo}", path, ref)

    if not content:
        raise HTTPException(status_code=404, detail="File not found")

    return FileContentModel(**content.__dict__)


@app.post("/repos/{owner}/{repo}/contents")
async def create_file(
    owner: str,
    repo: str,
    request: CreateFileRequest,
    user: dict = Depends(get_current_user),
):
    """Create a file in the repository."""
    client = get_github_client()
    success = await client.create_or_update_file(
        f"{owner}/{repo}",
        request.path,
        request.content,
        request.message,
        request.branch,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to create file")

    return {"status": "created", "path": request.path}


@app.put("/repos/{owner}/{repo}/contents")
async def update_file(
    owner: str,
    repo: str,
    request: UpdateFileRequest,
    user: dict = Depends(get_current_user),
):
    """Update a file in the repository."""
    client = get_github_client()
    success = await client.create_or_update_file(
        f"{owner}/{repo}",
        request.path,
        request.content,
        request.message,
        request.branch,
        request.sha,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update file")

    return {"status": "updated", "path": request.path}


# Search endpoint
@app.get("/search/code")
async def search_code(
    q: str,
    repo: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 30,
    user: dict = Depends(get_current_user),
):
    """Search code on GitHub."""
    client = get_github_client()
    results = await client.search_code(q, repo, language, limit)

    return {"results": results, "total": len(results)}


# Webhook endpoint
@app.post("/webhook")
async def handle_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    """Handle GitHub webhooks."""
    if not settings.github_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Verify signature
    body = await request.body()

    if x_hub_signature_256:
        expected_signature = "sha256=" + hmac.new(
            settings.github_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    logger.info(f"Received webhook event: {x_github_event}")

    # Handle different event types
    if x_github_event == "push":
        # Handle push event
        pass
    elif x_github_event == "pull_request":
        # Handle PR event
        pass
    elif x_github_event == "issues":
        # Handle issue event
        pass

    return {"status": "received", "event": x_github_event}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
