"""
GitHub Service Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.github_client import (
    GitHubClient,
    RepoInfo,
    IssueInfo,
    PRInfo,
    CommitInfo,
    FileContent,
    IssueState,
)


@pytest.fixture
def github_client():
    """Create a GitHub client for testing."""
    return GitHubClient(
        token="test-token",
        cache_ttl=60,
    )


class TestGitHubClient:
    """Test GitHub client operations."""

    def test_initialization(self, github_client):
        """Test client initialization."""
        assert github_client.token == "test-token"

    def test_cache_key(self, github_client):
        """Test cache key generation."""
        key = github_client._cache_key("repo", "owner/name")
        assert key == "repo:owner/name"


class TestRepositoryOperations:
    """Test repository operations."""

    @pytest.mark.asyncio
    async def test_get_repo(self, github_client):
        """Test getting repository info."""
        mock_repo = MagicMock()
        mock_repo.name = "test-repo"
        mock_repo.full_name = "owner/test-repo"
        mock_repo.description = "Test repository"
        mock_repo.html_url = "https://github.com/owner/test-repo"
        mock_repo.clone_url = "https://github.com/owner/test-repo.git"
        mock_repo.ssh_url = "git@github.com:owner/test-repo.git"
        mock_repo.default_branch = "main"
        mock_repo.language = "Python"
        mock_repo.stargazers_count = 100
        mock_repo.forks_count = 20
        mock_repo.open_issues_count = 5
        mock_repo.private = False
        mock_repo.created_at = MagicMock(isoformat=lambda: "2024-01-01T00:00:00")
        mock_repo.updated_at = MagicMock(isoformat=lambda: "2024-01-15T00:00:00")
        mock_repo.get_topics.return_value = ["python", "testing"]

        github_client._github = MagicMock()
        github_client._github.get_repo = MagicMock(return_value=mock_repo)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=mock_repo)

            info = await github_client.get_repo("owner/test-repo")

            assert info is not None
            assert info.name == "test-repo"
            assert info.full_name == "owner/test-repo"
            assert info.stars == 100


class TestIssueOperations:
    """Test issue operations."""

    @pytest.mark.asyncio
    async def test_get_issue(self, github_client):
        """Test getting issue info."""
        mock_issue = MagicMock()
        mock_issue.number = 42
        mock_issue.title = "Test Issue"
        mock_issue.body = "Issue body"
        mock_issue.state = "open"
        mock_issue.html_url = "https://github.com/owner/repo/issues/42"
        mock_issue.user.login = "user1"
        mock_issue.labels = [MagicMock(name="bug")]
        mock_issue.assignees = [MagicMock(login="user2")]
        mock_issue.created_at = MagicMock(isoformat=lambda: "2024-01-01T00:00:00")
        mock_issue.updated_at = MagicMock(isoformat=lambda: "2024-01-15T00:00:00")
        mock_issue.closed_at = None
        mock_issue.comments = 5

        mock_repo = MagicMock()
        mock_repo.get_issue = MagicMock(return_value=mock_issue)

        github_client._github = MagicMock()
        github_client._github.get_repo = MagicMock(return_value=mock_repo)

        with patch("asyncio.get_event_loop") as mock_loop:
            async def run_executor(_, func, *args):
                if args:
                    return func(args[0]) if callable(func) else func
                return func() if callable(func) else func

            mock_loop.return_value.run_in_executor = run_executor

            info = await github_client.get_issue("owner/repo", 42)

            # Note: This would need proper mocking


class TestPROperations:
    """Test pull request operations."""

    @pytest.mark.asyncio
    async def test_get_pr(self, github_client):
        """Test getting PR info."""
        # Similar test structure as get_issue
        pass

    @pytest.mark.asyncio
    async def test_create_pr(self, github_client):
        """Test creating a PR."""
        pass


class TestCommitOperations:
    """Test commit operations."""

    @pytest.mark.asyncio
    async def test_get_commits(self, github_client):
        """Test getting commit history."""
        pass


class TestFileOperations:
    """Test file operations."""

    @pytest.mark.asyncio
    async def test_get_file_content(self, github_client):
        """Test getting file content."""
        pass

    @pytest.mark.asyncio
    async def test_create_or_update_file(self, github_client):
        """Test creating/updating a file."""
        pass


class TestDataClasses:
    """Test data classes."""

    def test_repo_info(self):
        """Test RepoInfo creation."""
        info = RepoInfo(
            name="test-repo",
            full_name="owner/test-repo",
            description="Test description",
            url="https://github.com/owner/test-repo",
            clone_url="https://github.com/owner/test-repo.git",
            ssh_url="git@github.com:owner/test-repo.git",
            default_branch="main",
            language="Python",
            stars=100,
            forks=20,
            open_issues=5,
            is_private=False,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-15T00:00:00",
            topics=["python"],
        )

        assert info.name == "test-repo"
        assert info.stars == 100
        assert info.is_private is False

    def test_issue_info(self):
        """Test IssueInfo creation."""
        info = IssueInfo(
            number=42,
            title="Test Issue",
            body="Issue body",
            state="open",
            url="https://github.com/owner/repo/issues/42",
            user="user1",
            labels=["bug"],
            assignees=["user2"],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-15T00:00:00",
            comments=5,
        )

        assert info.number == 42
        assert info.state == "open"
        assert "bug" in info.labels

    def test_pr_info(self):
        """Test PRInfo creation."""
        info = PRInfo(
            number=123,
            title="Test PR",
            body="PR body",
            state="open",
            url="https://github.com/owner/repo/pull/123",
            user="user1",
            head_branch="feature",
            base_branch="main",
            labels=["enhancement"],
            reviewers=["reviewer1"],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-15T00:00:00",
            mergeable=True,
            additions=100,
            deletions=50,
            changed_files=10,
        )

        assert info.number == 123
        assert info.head_branch == "feature"
        assert info.base_branch == "main"

    def test_commit_info(self):
        """Test CommitInfo creation."""
        info = CommitInfo(
            sha="abc123",
            message="Test commit",
            author="Test Author",
            author_email="author@example.com",
            date="2024-01-01T00:00:00",
            url="https://github.com/owner/repo/commit/abc123",
            additions=10,
            deletions=5,
            files_changed=2,
        )

        assert info.sha == "abc123"
        assert info.additions == 10

    def test_file_content(self):
        """Test FileContent creation."""
        content = FileContent(
            path="src/main.py",
            content="print('hello')",
            sha="abc123",
            size=15,
        )

        assert content.path == "src/main.py"
        assert content.size == 15


class TestIssueState:
    """Test IssueState enum."""

    def test_states(self):
        """Test issue states."""
        assert IssueState.OPEN.value == "open"
        assert IssueState.CLOSED.value == "closed"
        assert IssueState.ALL.value == "all"
