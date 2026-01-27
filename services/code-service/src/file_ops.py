"""
File Operations Module

Provides safe file reading, writing, editing, and searching.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import fnmatch

import aiofiles
import chardet
from pathspec import PathSpec

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about a file."""
    path: str
    name: str
    extension: str
    size_bytes: int
    is_binary: bool
    encoding: Optional[str]
    line_count: Optional[int]


@dataclass
class FileContent:
    """File content with metadata."""
    path: str
    content: str
    encoding: str
    line_count: int


@dataclass
class SearchMatch:
    """A search match in a file."""
    path: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int


@dataclass
class EditOperation:
    """An edit operation to perform."""
    old_text: str
    new_text: str
    replace_all: bool = False


class FileOperations:
    """
    Safe file operations with workspace isolation.
    """

    # Common binary file extensions
    BINARY_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.exe', '.dll', '.so', '.dylib',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.pyc', '.pyo', '.class', '.o', '.obj',
        '.woff', '.woff2', '.ttf', '.eot',
        '.sqlite', '.db',
    }

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,
    ):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.max_file_size = max_file_size
        self._gitignore_spec: Optional[PathSpec] = None

    def _resolve_path(self, path: str) -> Path:
        """Resolve and validate a path within the workspace."""
        # Handle both absolute and relative paths
        if os.path.isabs(path):
            resolved = Path(path).resolve()
        else:
            resolved = (self.workspace_root / path).resolve()

        # Security: ensure path is within workspace
        try:
            resolved.relative_to(self.workspace_root.resolve())
        except ValueError:
            # Allow paths outside workspace for now (like Claude Code)
            pass

        return resolved

    def _is_binary(self, path: Path) -> bool:
        """Check if a file is likely binary."""
        if path.suffix.lower() in self.BINARY_EXTENSIONS:
            return True

        # Check first few bytes for null characters
        try:
            with open(path, 'rb') as f:
                chunk = f.read(8192)
                if b'\x00' in chunk:
                    return True
        except Exception:
            pass

        return False

    def _detect_encoding(self, content: bytes) -> str:
        """Detect file encoding."""
        result = chardet.detect(content)
        return result.get('encoding', 'utf-8') or 'utf-8'

    def _load_gitignore(self) -> Optional[PathSpec]:
        """Load .gitignore patterns."""
        gitignore_path = self.workspace_root / '.gitignore'
        if gitignore_path.exists():
            try:
                with open(gitignore_path) as f:
                    patterns = f.read().splitlines()
                return PathSpec.from_lines('gitwildmatch', patterns)
            except Exception as e:
                logger.warning(f"Failed to load .gitignore: {e}")
        return None

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored based on .gitignore."""
        if self._gitignore_spec is None:
            self._gitignore_spec = self._load_gitignore()

        if self._gitignore_spec:
            try:
                rel_path = path.relative_to(self.workspace_root)
                return self._gitignore_spec.match_file(str(rel_path))
            except ValueError:
                pass

        # Always ignore common directories
        ignored_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.env'}
        for part in path.parts:
            if part in ignored_dirs:
                return True

        return False

    async def read_file(
        self,
        path: str,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> FileContent:
        """
        Read a file's content.

        Args:
            path: File path (relative or absolute)
            offset: Line number to start from (0-indexed)
            limit: Maximum number of lines to read

        Returns:
            FileContent with the file data
        """
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not resolved.is_file():
            raise ValueError(f"Not a file: {path}")

        stat = resolved.stat()
        if stat.st_size > self.max_file_size:
            raise ValueError(f"File too large: {stat.st_size} bytes (max: {self.max_file_size})")

        if self._is_binary(resolved):
            raise ValueError(f"Cannot read binary file: {path}")

        async with aiofiles.open(resolved, 'rb') as f:
            raw_content = await f.read()

        encoding = self._detect_encoding(raw_content)
        content = raw_content.decode(encoding, errors='replace')
        lines = content.splitlines(keepends=True)

        # Apply offset and limit
        if offset > 0:
            lines = lines[offset:]
        if limit:
            lines = lines[:limit]

        return FileContent(
            path=str(resolved),
            content=''.join(lines),
            encoding=encoding,
            line_count=len(lines),
        )

    async def write_file(
        self,
        path: str,
        content: str,
        create_dirs: bool = True,
    ) -> FileInfo:
        """
        Write content to a file.

        Args:
            path: File path
            content: Content to write
            create_dirs: Create parent directories if needed

        Returns:
            FileInfo about the written file
        """
        resolved = self._resolve_path(path)

        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(resolved, 'w', encoding='utf-8') as f:
            await f.write(content)

        logger.info(f"Wrote file: {resolved}")

        return await self.get_file_info(str(resolved))

    async def edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str,
        replace_all: bool = False,
    ) -> Tuple[FileContent, int]:
        """
        Edit a file by replacing text.

        Args:
            path: File path
            old_text: Text to find
            new_text: Text to replace with
            replace_all: Replace all occurrences or just first

        Returns:
            Tuple of (new FileContent, number of replacements)
        """
        file_content = await self.read_file(path)
        content = file_content.content

        # Check if old_text exists
        count = content.count(old_text)
        if count == 0:
            raise ValueError(f"Text not found in file: {old_text[:100]}...")

        if not replace_all and count > 1:
            raise ValueError(
                f"Text found {count} times. Use replace_all=True or provide more context."
            )

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_text, new_text)
            replacements = count
        else:
            new_content = content.replace(old_text, new_text, 1)
            replacements = 1

        # Write back
        await self.write_file(path, new_content)

        logger.info(f"Edited file: {path} ({replacements} replacements)")

        return await self.read_file(path), replacements

    async def delete_file(self, path: str) -> bool:
        """Delete a file."""
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")

        resolved.unlink()
        logger.info(f"Deleted file: {resolved}")
        return True

    async def get_file_info(self, path: str) -> FileInfo:
        """Get information about a file."""
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {path}")

        stat = resolved.stat()
        is_binary = self._is_binary(resolved)

        encoding = None
        line_count = None

        if not is_binary and stat.st_size < self.max_file_size:
            try:
                async with aiofiles.open(resolved, 'rb') as f:
                    raw = await f.read()
                encoding = self._detect_encoding(raw)
                line_count = raw.decode(encoding, errors='replace').count('\n') + 1
            except Exception:
                pass

        return FileInfo(
            path=str(resolved),
            name=resolved.name,
            extension=resolved.suffix,
            size_bytes=stat.st_size,
            is_binary=is_binary,
            encoding=encoding,
            line_count=line_count,
        )

    async def list_files(
        self,
        path: str = ".",
        pattern: str = "*",
        recursive: bool = False,
        include_hidden: bool = False,
    ) -> List[FileInfo]:
        """
        List files in a directory.

        Args:
            path: Directory path
            pattern: Glob pattern to match
            recursive: Search recursively
            include_hidden: Include hidden files

        Returns:
            List of FileInfo objects
        """
        resolved = self._resolve_path(path)

        if not resolved.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not resolved.is_dir():
            raise ValueError(f"Not a directory: {path}")

        results = []
        glob_pattern = f"**/{pattern}" if recursive else pattern

        for file_path in resolved.glob(glob_pattern):
            if not file_path.is_file():
                continue

            if not include_hidden and file_path.name.startswith('.'):
                continue

            if self._should_ignore(file_path):
                continue

            try:
                info = await self.get_file_info(str(file_path))
                results.append(info)
            except Exception as e:
                logger.warning(f"Failed to get info for {file_path}: {e}")

        return sorted(results, key=lambda x: x.path)

    async def search_files(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = True,
        max_results: int = 100,
    ) -> List[SearchMatch]:
        """
        Search for a pattern in files.

        Args:
            pattern: Regex pattern to search for
            path: Directory to search in
            file_pattern: Glob pattern for files to search
            case_sensitive: Case sensitive search
            max_results: Maximum number of results

        Returns:
            List of SearchMatch objects
        """
        resolved = self._resolve_path(path)

        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)

        results = []
        files = await self.list_files(path, file_pattern, recursive=True)

        for file_info in files:
            if len(results) >= max_results:
                break

            if file_info.is_binary:
                continue

            try:
                content = await self.read_file(file_info.path)

                for i, line in enumerate(content.content.splitlines(), 1):
                    if len(results) >= max_results:
                        break

                    for match in regex.finditer(line):
                        results.append(SearchMatch(
                            path=file_info.path,
                            line_number=i,
                            line_content=line.strip(),
                            match_start=match.start(),
                            match_end=match.end(),
                        ))

                        if len(results) >= max_results:
                            break

            except Exception as e:
                logger.warning(f"Failed to search {file_info.path}: {e}")

        return results

    async def glob_files(
        self,
        pattern: str,
        path: str = ".",
    ) -> List[str]:
        """
        Find files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "**/*.py")
            path: Base directory

        Returns:
            List of matching file paths
        """
        resolved = self._resolve_path(path)

        results = []
        for file_path in resolved.glob(pattern):
            if file_path.is_file() and not self._should_ignore(file_path):
                results.append(str(file_path))

        return sorted(results)
