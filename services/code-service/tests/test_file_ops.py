"""
File Operations Tests
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.file_ops import FileOperations


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def file_ops(temp_workspace):
    """Create FileOperations instance with temp workspace."""
    return FileOperations(workspace_root=temp_workspace)


class TestFileOperations:
    """Test file operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, file_ops, temp_workspace):
        """Test writing and reading a file."""
        content = "Hello, JARVIS!"
        path = "test.txt"

        # Write
        info = await file_ops.write_file(path, content)
        assert info.name == "test.txt"
        assert info.size_bytes == len(content)

        # Read
        result = await file_ops.read_file(path)
        assert result.content == content
        assert result.encoding == "utf-8"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, file_ops):
        """Test reading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            await file_ops.read_file("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_edit_file(self, file_ops):
        """Test editing a file."""
        # Create file
        await file_ops.write_file("test.txt", "Hello World")

        # Edit
        result, count = await file_ops.edit_file(
            "test.txt",
            "World",
            "JARVIS"
        )

        assert count == 1
        assert "JARVIS" in result.content
        assert "World" not in result.content

    @pytest.mark.asyncio
    async def test_edit_file_replace_all(self, file_ops):
        """Test editing with replace_all."""
        await file_ops.write_file("test.txt", "foo bar foo baz foo")

        result, count = await file_ops.edit_file(
            "test.txt",
            "foo",
            "qux",
            replace_all=True
        )

        assert count == 3
        assert "foo" not in result.content
        assert result.content.count("qux") == 3

    @pytest.mark.asyncio
    async def test_edit_file_ambiguous(self, file_ops):
        """Test that edit fails when text appears multiple times without replace_all."""
        await file_ops.write_file("test.txt", "foo foo foo")

        with pytest.raises(ValueError, match="found 3 times"):
            await file_ops.edit_file("test.txt", "foo", "bar")

    @pytest.mark.asyncio
    async def test_delete_file(self, file_ops, temp_workspace):
        """Test deleting a file."""
        await file_ops.write_file("test.txt", "content")

        result = await file_ops.delete_file("test.txt")
        assert result is True

        with pytest.raises(FileNotFoundError):
            await file_ops.read_file("test.txt")

    @pytest.mark.asyncio
    async def test_list_files(self, file_ops):
        """Test listing files."""
        # Create some files
        await file_ops.write_file("file1.txt", "content1")
        await file_ops.write_file("file2.txt", "content2")
        await file_ops.write_file("subdir/file3.txt", "content3")

        # List non-recursive
        files = await file_ops.list_files(".", "*.txt", recursive=False)
        assert len(files) == 2

        # List recursive
        files = await file_ops.list_files(".", "*.txt", recursive=True)
        assert len(files) == 3

    @pytest.mark.asyncio
    async def test_search_files(self, file_ops):
        """Test searching files."""
        await file_ops.write_file("test1.txt", "Hello JARVIS, how are you?")
        await file_ops.write_file("test2.txt", "JARVIS is the best assistant")
        await file_ops.write_file("test3.txt", "No match here")

        matches = await file_ops.search_files("JARVIS", ".", "*.txt")
        assert len(matches) == 2

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, file_ops):
        """Test case-insensitive search."""
        await file_ops.write_file("test.txt", "Hello jarvis")

        # Case sensitive - no match
        matches = await file_ops.search_files("JARVIS", ".", "*.txt", case_sensitive=True)
        assert len(matches) == 0

        # Case insensitive - match
        matches = await file_ops.search_files("JARVIS", ".", "*.txt", case_sensitive=False)
        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_glob_files(self, file_ops):
        """Test glob file matching."""
        await file_ops.write_file("file1.py", "python")
        await file_ops.write_file("file2.py", "python")
        await file_ops.write_file("file3.txt", "text")

        py_files = await file_ops.glob_files("*.py")
        assert len(py_files) == 2

        all_files = await file_ops.glob_files("*.*")
        assert len(all_files) == 3

    @pytest.mark.asyncio
    async def test_get_file_info(self, file_ops):
        """Test getting file info."""
        content = "Line 1\nLine 2\nLine 3"
        await file_ops.write_file("test.txt", content)

        info = await file_ops.get_file_info("test.txt")

        assert info.name == "test.txt"
        assert info.extension == ".txt"
        assert info.is_binary is False
        assert info.line_count == 3

    @pytest.mark.asyncio
    async def test_binary_detection(self, file_ops, temp_workspace):
        """Test binary file detection."""
        # Create a binary file
        binary_path = Path(temp_workspace) / "test.png"
        binary_path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        info = await file_ops.get_file_info("test.png")
        assert info.is_binary is True

    @pytest.mark.asyncio
    async def test_read_with_offset_and_limit(self, file_ops):
        """Test reading with offset and limit."""
        content = "\n".join([f"Line {i}" for i in range(10)])
        await file_ops.write_file("test.txt", content)

        result = await file_ops.read_file("test.txt", offset=2, limit=3)

        lines = result.content.strip().split('\n')
        assert len(lines) == 3
        assert "Line 2" in result.content


class TestFileOperationsEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_create_nested_directories(self, file_ops):
        """Test creating nested directories."""
        await file_ops.write_file("a/b/c/test.txt", "content")
        result = await file_ops.read_file("a/b/c/test.txt")
        assert result.content == "content"

    @pytest.mark.asyncio
    async def test_unicode_content(self, file_ops):
        """Test handling unicode content."""
        content = "Hello 世界! 🎉"
        await file_ops.write_file("unicode.txt", content)
        result = await file_ops.read_file("unicode.txt")
        assert result.content == content

    @pytest.mark.asyncio
    async def test_empty_file(self, file_ops):
        """Test handling empty file."""
        await file_ops.write_file("empty.txt", "")
        result = await file_ops.read_file("empty.txt")
        assert result.content == ""
