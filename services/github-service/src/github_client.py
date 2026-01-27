"""
GitHub API Client

Provides GitHub API integration for repository, issue, and PR management.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from github import Github, GithubException
from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Commit import Commit
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class IssueState(str, Enum):
    """Issue/PR states."""
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


class PRState(str, Enum):
    """PR states."""
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


@dataclass
class RepoInfo:
    """Repository information."""
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
    topics: List[str] = field(default_factory=list)


@dataclass
class IssueInfo:
    """Issue information."""
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


@dataclass
class PRInfo:
    """Pull request information."""
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


@dataclass
class CommitInfo:
    """Commit information."""
    sha: str
    message: str
    author: str
    author_email: str
    date: str
    url: str
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0


@dataclass
class FileContent:
    """File content from a repository."""
    path: str
    content: str
    sha: str
    size: int
    encoding: str = "utf-8"


class GitHubClient:
    """
    GitHub API client.

    Features:
    - Repository management
    - Issue and PR operations
    - Commit history
    - File operations
    - Webhook handling
    """

    def __init__(
        self,
        token: str,
        cache_ttl: int = 300,
    ):
        self.token = token
        self._github = Github(token)
        self._cache = TTLCache(maxsize=1000, ttl=cache_ttl)
        self._user = None

    @property
    def user(self):
        """Get authenticated user."""
        if self._user is None:
            self._user = self._github.get_user()
        return self._user

    def _cache_key(self, *args) -> str:
        """Generate cache key."""
        return ":".join(str(a) for a in args)

    async def get_repo(self, repo_name: str) -> Optional[RepoInfo]:
        """
        Get repository information.

        Args:
            repo_name: Repository name (owner/repo)

        Returns:
            RepoInfo or None
        """
        cache_key = self._cache_key("repo", repo_name)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)

            info = RepoInfo(
                name=repo.name,
                full_name=repo.full_name,
                description=repo.description,
                url=repo.html_url,
                clone_url=repo.clone_url,
                ssh_url=repo.ssh_url,
                default_branch=repo.default_branch,
                language=repo.language,
                stars=repo.stargazers_count,
                forks=repo.forks_count,
                open_issues=repo.open_issues_count,
                is_private=repo.private,
                created_at=repo.created_at.isoformat(),
                updated_at=repo.updated_at.isoformat(),
                topics=repo.get_topics(),
            )

            self._cache[cache_key] = info
            return info

        except GithubException as e:
            logger.error(f"Failed to get repo {repo_name}: {e}")
            return None

    async def list_repos(
        self,
        user: Optional[str] = None,
        type: str = "all",
        sort: str = "updated",
        limit: int = 30,
    ) -> List[RepoInfo]:
        """
        List repositories.

        Args:
            user: Username (None for authenticated user)
            type: Repo type (all, owner, public, private, member)
            sort: Sort by (created, updated, pushed, full_name)
            limit: Maximum repos to return

        Returns:
            List of RepoInfo
        """
        try:
            loop = asyncio.get_event_loop()

            if user:
                github_user = await loop.run_in_executor(
                    None, self._github.get_user, user
                )
                repos = github_user.get_repos(type=type, sort=sort)
            else:
                repos = self.user.get_repos(type=type, sort=sort)

            result = []
            for repo in repos[:limit]:
                result.append(RepoInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    description=repo.description,
                    url=repo.html_url,
                    clone_url=repo.clone_url,
                    ssh_url=repo.ssh_url,
                    default_branch=repo.default_branch,
                    language=repo.language,
                    stars=repo.stargazers_count,
                    forks=repo.forks_count,
                    open_issues=repo.open_issues_count,
                    is_private=repo.private,
                    created_at=repo.created_at.isoformat(),
                    updated_at=repo.updated_at.isoformat(),
                ))

            return result

        except GithubException as e:
            logger.error(f"Failed to list repos: {e}")
            return []

    async def get_issue(self, repo_name: str, issue_number: int) -> Optional[IssueInfo]:
        """Get an issue by number."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)
            issue = await loop.run_in_executor(None, repo.get_issue, issue_number)

            return IssueInfo(
                number=issue.number,
                title=issue.title,
                body=issue.body,
                state=issue.state,
                url=issue.html_url,
                user=issue.user.login,
                labels=[l.name for l in issue.labels],
                assignees=[a.login for a in issue.assignees],
                created_at=issue.created_at.isoformat(),
                updated_at=issue.updated_at.isoformat(),
                closed_at=issue.closed_at.isoformat() if issue.closed_at else None,
                comments=issue.comments,
            )

        except GithubException as e:
            logger.error(f"Failed to get issue {repo_name}#{issue_number}: {e}")
            return None

    async def list_issues(
        self,
        repo_name: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        limit: int = 30,
    ) -> List[IssueInfo]:
        """List issues in a repository."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)

            kwargs = {"state": state}
            if labels:
                kwargs["labels"] = labels
            if assignee:
                kwargs["assignee"] = assignee

            issues = repo.get_issues(**kwargs)

            result = []
            for issue in issues[:limit]:
                # Skip pull requests (they're also issues in GitHub API)
                if issue.pull_request:
                    continue

                result.append(IssueInfo(
                    number=issue.number,
                    title=issue.title,
                    body=issue.body,
                    state=issue.state,
                    url=issue.html_url,
                    user=issue.user.login,
                    labels=[l.name for l in issue.labels],
                    assignees=[a.login for a in issue.assignees],
                    created_at=issue.created_at.isoformat(),
                    updated_at=issue.updated_at.isoformat(),
                    closed_at=issue.closed_at.isoformat() if issue.closed_at else None,
                    comments=issue.comments,
                ))

            return result

        except GithubException as e:
            logger.error(f"Failed to list issues for {repo_name}: {e}")
            return []

    async def create_issue(
        self,
        repo_name: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Optional[IssueInfo]:
        """Create a new issue."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)

            kwargs = {"title": title}
            if body:
                kwargs["body"] = body
            if labels:
                kwargs["labels"] = labels
            if assignees:
                kwargs["assignees"] = assignees

            issue = await loop.run_in_executor(None, lambda: repo.create_issue(**kwargs))

            return IssueInfo(
                number=issue.number,
                title=issue.title,
                body=issue.body,
                state=issue.state,
                url=issue.html_url,
                user=issue.user.login,
                labels=[l.name for l in issue.labels],
                assignees=[a.login for a in issue.assignees],
                created_at=issue.created_at.isoformat(),
                updated_at=issue.updated_at.isoformat(),
            )

        except GithubException as e:
            logger.error(f"Failed to create issue in {repo_name}: {e}")
            return None

    async def close_issue(self, repo_name: str, issue_number: int) -> bool:
        """Close an issue."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)
            issue = await loop.run_in_executor(None, repo.get_issue, issue_number)
            await loop.run_in_executor(None, issue.edit, state="closed")
            return True
        except GithubException as e:
            logger.error(f"Failed to close issue {repo_name}#{issue_number}: {e}")
            return False

    async def add_issue_comment(
        self,
        repo_name: str,
        issue_number: int,
        body: str,
    ) -> bool:
        """Add a comment to an issue."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)
            issue = await loop.run_in_executor(None, repo.get_issue, issue_number)
            await loop.run_in_executor(None, issue.create_comment, body)
            return True
        except GithubException as e:
            logger.error(f"Failed to comment on {repo_name}#{issue_number}: {e}")
            return False

    async def get_pr(self, repo_name: str, pr_number: int) -> Optional[PRInfo]:
        """Get a pull request by number."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)
            pr = await loop.run_in_executor(None, repo.get_pull, pr_number)

            return PRInfo(
                number=pr.number,
                title=pr.title,
                body=pr.body,
                state=pr.state,
                url=pr.html_url,
                user=pr.user.login,
                head_branch=pr.head.ref,
                base_branch=pr.base.ref,
                labels=[l.name for l in pr.labels],
                reviewers=[r.login for r in pr.get_review_requests()[0]],
                created_at=pr.created_at.isoformat(),
                updated_at=pr.updated_at.isoformat(),
                merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
                closed_at=pr.closed_at.isoformat() if pr.closed_at else None,
                mergeable=pr.mergeable,
                additions=pr.additions,
                deletions=pr.deletions,
                changed_files=pr.changed_files,
            )

        except GithubException as e:
            logger.error(f"Failed to get PR {repo_name}#{pr_number}: {e}")
            return None

    async def list_prs(
        self,
        repo_name: str,
        state: str = "open",
        base: Optional[str] = None,
        head: Optional[str] = None,
        limit: int = 30,
    ) -> List[PRInfo]:
        """List pull requests in a repository."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)

            kwargs = {"state": state}
            if base:
                kwargs["base"] = base
            if head:
                kwargs["head"] = head

            prs = repo.get_pulls(**kwargs)

            result = []
            for pr in prs[:limit]:
                result.append(PRInfo(
                    number=pr.number,
                    title=pr.title,
                    body=pr.body,
                    state=pr.state,
                    url=pr.html_url,
                    user=pr.user.login,
                    head_branch=pr.head.ref,
                    base_branch=pr.base.ref,
                    labels=[l.name for l in pr.labels],
                    reviewers=[],
                    created_at=pr.created_at.isoformat(),
                    updated_at=pr.updated_at.isoformat(),
                    merged_at=pr.merged_at.isoformat() if pr.merged_at else None,
                    additions=pr.additions,
                    deletions=pr.deletions,
                    changed_files=pr.changed_files,
                ))

            return result

        except GithubException as e:
            logger.error(f"Failed to list PRs for {repo_name}: {e}")
            return []

    async def create_pr(
        self,
        repo_name: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        draft: bool = False,
    ) -> Optional[PRInfo]:
        """Create a pull request."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)

            pr = await loop.run_in_executor(
                None,
                lambda: repo.create_pull(
                    title=title,
                    body=body or "",
                    head=head,
                    base=base,
                    draft=draft,
                )
            )

            return PRInfo(
                number=pr.number,
                title=pr.title,
                body=pr.body,
                state=pr.state,
                url=pr.html_url,
                user=pr.user.login,
                head_branch=pr.head.ref,
                base_branch=pr.base.ref,
                labels=[],
                reviewers=[],
                created_at=pr.created_at.isoformat(),
                updated_at=pr.updated_at.isoformat(),
            )

        except GithubException as e:
            logger.error(f"Failed to create PR in {repo_name}: {e}")
            return None

    async def merge_pr(
        self,
        repo_name: str,
        pr_number: int,
        commit_message: Optional[str] = None,
        merge_method: str = "merge",  # merge, squash, rebase
    ) -> bool:
        """Merge a pull request."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)
            pr = await loop.run_in_executor(None, repo.get_pull, pr_number)

            await loop.run_in_executor(
                None,
                lambda: pr.merge(
                    commit_message=commit_message,
                    merge_method=merge_method,
                )
            )
            return True

        except GithubException as e:
            logger.error(f"Failed to merge PR {repo_name}#{pr_number}: {e}")
            return False

    async def get_commits(
        self,
        repo_name: str,
        branch: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 30,
    ) -> List[CommitInfo]:
        """Get commit history."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)

            kwargs = {}
            if branch:
                kwargs["sha"] = branch
            if since:
                kwargs["since"] = since

            commits = repo.get_commits(**kwargs)

            result = []
            for commit in commits[:limit]:
                result.append(CommitInfo(
                    sha=commit.sha,
                    message=commit.commit.message,
                    author=commit.commit.author.name,
                    author_email=commit.commit.author.email,
                    date=commit.commit.author.date.isoformat(),
                    url=commit.html_url,
                    additions=commit.stats.additions if commit.stats else 0,
                    deletions=commit.stats.deletions if commit.stats else 0,
                    files_changed=len(commit.files) if commit.files else 0,
                ))

            return result

        except GithubException as e:
            logger.error(f"Failed to get commits for {repo_name}: {e}")
            return []

    async def get_file_content(
        self,
        repo_name: str,
        path: str,
        ref: Optional[str] = None,
    ) -> Optional[FileContent]:
        """Get file content from repository."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)

            kwargs = {"path": path}
            if ref:
                kwargs["ref"] = ref

            content = await loop.run_in_executor(
                None, lambda: repo.get_contents(**kwargs)
            )

            if isinstance(content, list):
                # It's a directory
                return None

            return FileContent(
                path=content.path,
                content=content.decoded_content.decode("utf-8"),
                sha=content.sha,
                size=content.size,
            )

        except GithubException as e:
            logger.error(f"Failed to get file {repo_name}/{path}: {e}")
            return None

    async def create_or_update_file(
        self,
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: Optional[str] = None,
        sha: Optional[str] = None,
    ) -> bool:
        """Create or update a file in a repository."""
        try:
            loop = asyncio.get_event_loop()
            repo = await loop.run_in_executor(None, self._github.get_repo, repo_name)

            kwargs = {
                "path": path,
                "message": message,
                "content": content.encode("utf-8"),
            }

            if branch:
                kwargs["branch"] = branch

            if sha:
                # Update existing file
                kwargs["sha"] = sha
                await loop.run_in_executor(
                    None, lambda: repo.update_file(**kwargs)
                )
            else:
                # Create new file
                await loop.run_in_executor(
                    None, lambda: repo.create_file(**kwargs)
                )

            return True

        except GithubException as e:
            logger.error(f"Failed to create/update file {repo_name}/{path}: {e}")
            return False

    async def search_code(
        self,
        query: str,
        repo: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """Search code on GitHub."""
        try:
            search_query = query
            if repo:
                search_query += f" repo:{repo}"
            if language:
                search_query += f" language:{language}"

            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self._github.search_code, search_query
            )

            output = []
            for item in results[:limit]:
                output.append({
                    "name": item.name,
                    "path": item.path,
                    "repository": item.repository.full_name,
                    "url": item.html_url,
                    "sha": item.sha,
                })

            return output

        except GithubException as e:
            logger.error(f"Code search failed: {e}")
            return []


# Singleton instance
_github_client: Optional[GitHubClient] = None


def get_github_client() -> GitHubClient:
    """Get or create the GitHub client singleton."""
    global _github_client
    if _github_client is None:
        from .config import get_settings
        settings = get_settings()
        _github_client = GitHubClient(
            token=settings.github_token,
            cache_ttl=settings.cache_ttl_seconds,
        )
    return _github_client
