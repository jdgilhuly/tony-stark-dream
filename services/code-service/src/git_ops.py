"""
Git Operations Module

Provides git operations: status, diff, commit, branch, push, pull, etc.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
from enum import Enum

from git import Repo, GitCommandError
from git.diff import Diff

logger = logging.getLogger(__name__)


class FileStatus(str, Enum):
    """Git file status."""
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNTRACKED = "?"
    IGNORED = "!"


@dataclass
class StatusFile:
    """A file in git status."""
    path: str
    status: FileStatus
    staged: bool
    old_path: Optional[str] = None  # For renames


@dataclass
class GitStatus:
    """Git repository status."""
    branch: str
    ahead: int
    behind: int
    staged: List[StatusFile]
    unstaged: List[StatusFile]
    untracked: List[str]
    is_clean: bool


@dataclass
class CommitInfo:
    """Information about a commit."""
    sha: str
    short_sha: str
    message: str
    author: str
    author_email: str
    date: str
    files_changed: int


@dataclass
class DiffHunk:
    """A diff hunk."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: str


@dataclass
class FileDiff:
    """Diff for a single file."""
    path: str
    old_path: Optional[str]
    status: FileStatus
    hunks: List[DiffHunk]
    additions: int
    deletions: int


@dataclass
class BranchInfo:
    """Information about a branch."""
    name: str
    is_current: bool
    tracking: Optional[str]
    ahead: int
    behind: int
    last_commit: Optional[str]


class GitOperations:
    """
    Git operations for a repository.
    """

    def __init__(
        self,
        repo_path: Optional[str] = None,
        author_name: str = "JARVIS",
        author_email: str = "jarvis@local",
    ):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.author_name = author_name
        self.author_email = author_email
        self._repo: Optional[Repo] = None

    @property
    def repo(self) -> Repo:
        """Get or initialize the git repository."""
        if self._repo is None:
            try:
                self._repo = Repo(self.repo_path, search_parent_directories=True)
            except Exception as e:
                raise ValueError(f"Not a git repository: {self.repo_path}") from e
        return self._repo

    def _get_status_enum(self, status_char: str) -> FileStatus:
        """Convert git status character to enum."""
        mapping = {
            'A': FileStatus.ADDED,
            'M': FileStatus.MODIFIED,
            'D': FileStatus.DELETED,
            'R': FileStatus.RENAMED,
            'C': FileStatus.COPIED,
            '?': FileStatus.UNTRACKED,
            '!': FileStatus.IGNORED,
        }
        return mapping.get(status_char, FileStatus.MODIFIED)

    def get_status(self) -> GitStatus:
        """Get repository status."""
        staged = []
        unstaged = []
        untracked = []

        # Get current branch info
        try:
            branch = self.repo.active_branch.name
        except TypeError:
            branch = "HEAD (detached)"

        # Calculate ahead/behind
        ahead = 0
        behind = 0
        try:
            tracking = self.repo.active_branch.tracking_branch()
            if tracking:
                commits_behind = list(self.repo.iter_commits(f'{branch}..{tracking}'))
                commits_ahead = list(self.repo.iter_commits(f'{tracking}..{branch}'))
                ahead = len(commits_ahead)
                behind = len(commits_behind)
        except Exception:
            pass

        # Staged changes
        for diff in self.repo.index.diff(self.repo.head.commit):
            status = self._get_status_enum(diff.change_type[0].upper())
            staged.append(StatusFile(
                path=diff.b_path or diff.a_path,
                status=status,
                staged=True,
                old_path=diff.a_path if diff.renamed else None,
            ))

        # Unstaged changes
        for diff in self.repo.index.diff(None):
            status = self._get_status_enum(diff.change_type[0].upper())
            unstaged.append(StatusFile(
                path=diff.b_path or diff.a_path,
                status=status,
                staged=False,
            ))

        # Untracked files
        untracked = list(self.repo.untracked_files)

        is_clean = len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0

        return GitStatus(
            branch=branch,
            ahead=ahead,
            behind=behind,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            is_clean=is_clean,
        )

    def get_diff(
        self,
        staged: bool = False,
        path: Optional[str] = None,
        commit: Optional[str] = None,
    ) -> List[FileDiff]:
        """
        Get diff of changes.

        Args:
            staged: Get staged changes (vs HEAD)
            path: Specific file path
            commit: Compare against specific commit

        Returns:
            List of FileDiff objects
        """
        results = []

        if commit:
            # Diff against specific commit
            base = self.repo.commit(commit)
            diffs = base.diff(self.repo.head.commit)
        elif staged:
            # Staged changes
            diffs = self.repo.index.diff(self.repo.head.commit, create_patch=True)
        else:
            # Unstaged changes
            diffs = self.repo.index.diff(None, create_patch=True)

        for diff in diffs:
            if path and diff.b_path != path and diff.a_path != path:
                continue

            status = self._get_status_enum(diff.change_type[0].upper())

            # Parse hunks from diff
            hunks = []
            additions = 0
            deletions = 0

            if diff.diff:
                diff_text = diff.diff.decode('utf-8', errors='replace')
                # Simple hunk counting (full parsing would be more complex)
                for line in diff_text.split('\n'):
                    if line.startswith('+') and not line.startswith('+++'):
                        additions += 1
                    elif line.startswith('-') and not line.startswith('---'):
                        deletions += 1

                hunks.append(DiffHunk(
                    old_start=0,
                    old_count=0,
                    new_start=0,
                    new_count=0,
                    content=diff_text,
                ))

            results.append(FileDiff(
                path=diff.b_path or diff.a_path,
                old_path=diff.a_path if diff.renamed else None,
                status=status,
                hunks=hunks,
                additions=additions,
                deletions=deletions,
            ))

        return results

    def add_files(self, paths: List[str]) -> List[str]:
        """
        Stage files for commit.

        Args:
            paths: List of file paths to stage

        Returns:
            List of staged file paths
        """
        staged = []
        for path in paths:
            try:
                self.repo.index.add([path])
                staged.append(path)
                logger.info(f"Staged: {path}")
            except Exception as e:
                logger.warning(f"Failed to stage {path}: {e}")

        return staged

    def add_all(self) -> List[str]:
        """Stage all changes."""
        self.repo.git.add(A=True)
        status = self.get_status()
        return [f.path for f in status.staged]

    def reset_files(self, paths: List[str]) -> List[str]:
        """
        Unstage files.

        Args:
            paths: List of file paths to unstage

        Returns:
            List of unstaged file paths
        """
        unstaged = []
        for path in paths:
            try:
                self.repo.index.reset(paths=[path])
                unstaged.append(path)
                logger.info(f"Unstaged: {path}")
            except Exception as e:
                logger.warning(f"Failed to unstage {path}: {e}")

        return unstaged

    def commit(
        self,
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> CommitInfo:
        """
        Create a commit.

        Args:
            message: Commit message
            author_name: Override author name
            author_email: Override author email

        Returns:
            CommitInfo about the created commit
        """
        name = author_name or self.author_name
        email = author_email or self.author_email

        # Set author
        self.repo.config_writer().set_value("user", "name", name).release()
        self.repo.config_writer().set_value("user", "email", email).release()

        # Create commit
        commit = self.repo.index.commit(message)

        logger.info(f"Created commit: {commit.hexsha[:8]} - {message[:50]}")

        return CommitInfo(
            sha=commit.hexsha,
            short_sha=commit.hexsha[:8],
            message=commit.message.strip(),
            author=name,
            author_email=email,
            date=commit.authored_datetime.isoformat(),
            files_changed=len(commit.stats.files),
        )

    def get_log(
        self,
        max_count: int = 10,
        path: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> List[CommitInfo]:
        """
        Get commit log.

        Args:
            max_count: Maximum number of commits
            path: Filter by file path
            branch: Branch to get log from

        Returns:
            List of CommitInfo objects
        """
        results = []

        kwargs = {'max_count': max_count}
        if path:
            kwargs['paths'] = path

        ref = branch or 'HEAD'

        for commit in self.repo.iter_commits(ref, **kwargs):
            results.append(CommitInfo(
                sha=commit.hexsha,
                short_sha=commit.hexsha[:8],
                message=commit.message.strip().split('\n')[0],
                author=commit.author.name,
                author_email=commit.author.email,
                date=commit.authored_datetime.isoformat(),
                files_changed=len(commit.stats.files),
            ))

        return results

    def get_branches(self) -> List[BranchInfo]:
        """Get list of branches."""
        results = []
        current = self.repo.active_branch.name if not self.repo.head.is_detached else None

        for branch in self.repo.branches:
            tracking = None
            ahead = 0
            behind = 0

            try:
                tracking_branch = branch.tracking_branch()
                if tracking_branch:
                    tracking = tracking_branch.name
                    ahead = len(list(self.repo.iter_commits(f'{tracking}..{branch}')))
                    behind = len(list(self.repo.iter_commits(f'{branch}..{tracking}')))
            except Exception:
                pass

            last_commit = None
            try:
                last_commit = branch.commit.hexsha[:8]
            except Exception:
                pass

            results.append(BranchInfo(
                name=branch.name,
                is_current=branch.name == current,
                tracking=tracking,
                ahead=ahead,
                behind=behind,
                last_commit=last_commit,
            ))

        return results

    def create_branch(self, name: str, checkout: bool = True) -> BranchInfo:
        """Create a new branch."""
        branch = self.repo.create_head(name)

        if checkout:
            branch.checkout()

        logger.info(f"Created branch: {name}")

        return BranchInfo(
            name=branch.name,
            is_current=checkout,
            tracking=None,
            ahead=0,
            behind=0,
            last_commit=branch.commit.hexsha[:8],
        )

    def checkout(self, ref: str) -> str:
        """Checkout a branch or commit."""
        self.repo.git.checkout(ref)
        logger.info(f"Checked out: {ref}")
        return ref

    def push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        set_upstream: bool = False,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """
        Push to remote.

        Args:
            remote: Remote name
            branch: Branch to push
            set_upstream: Set upstream tracking
            force: Force push

        Returns:
            Tuple of (success, message)
        """
        try:
            branch = branch or self.repo.active_branch.name
            remote_obj = self.repo.remote(remote)

            args = []
            if set_upstream:
                args.extend(['-u'])
            if force:
                args.extend(['-f'])

            result = remote_obj.push(branch, *args)

            logger.info(f"Pushed {branch} to {remote}")
            return True, f"Pushed {branch} to {remote}"

        except GitCommandError as e:
            logger.error(f"Push failed: {e}")
            return False, str(e)

    def pull(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        rebase: bool = False,
    ) -> Tuple[bool, str]:
        """
        Pull from remote.

        Args:
            remote: Remote name
            branch: Branch to pull
            rebase: Use rebase instead of merge

        Returns:
            Tuple of (success, message)
        """
        try:
            remote_obj = self.repo.remote(remote)

            if rebase:
                self.repo.git.pull('--rebase', remote, branch or '')
            else:
                remote_obj.pull(branch)

            logger.info(f"Pulled from {remote}")
            return True, f"Pulled from {remote}"

        except GitCommandError as e:
            logger.error(f"Pull failed: {e}")
            return False, str(e)

    def stash(self, message: Optional[str] = None) -> str:
        """Stash changes."""
        args = ['save']
        if message:
            args.append(message)

        self.repo.git.stash(*args)
        logger.info("Stashed changes")
        return "Changes stashed"

    def stash_pop(self) -> str:
        """Pop stashed changes."""
        self.repo.git.stash('pop')
        logger.info("Popped stash")
        return "Stash popped"
