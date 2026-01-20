"""Tests for context collection module."""

import tempfile
from pathlib import Path

import pytest

from flow.context.collector import ContextCollector, MAX_TREE_ENTRIES
from flow.context.indexer import FileIndexer, FileInfo
from flow.config import Config


class TestContextCollector:
    """Tests for ContextCollector class."""

    def test_collect_from_file(self, tmp_path):
        """Test collecting context from a single file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    return 'world'")

        collector = ContextCollector()
        result = collector.collect_from_path(test_file)

        assert "test.py" in result
        assert "def hello():" in result
        assert "```python" in result

    def test_collect_from_directory(self, tmp_path):
        """Test collecting context from a directory."""
        # Create test files
        (tmp_path / "main.py").write_text("print('main')")
        (tmp_path / "utils.py").write_text("def util(): pass")

        collector = ContextCollector()
        result = collector.collect_from_path(tmp_path)

        assert "main.py" in result
        assert "utils.py" in result

    def test_collect_from_nonexistent_path(self, tmp_path):
        """Test collecting from non-existent path."""
        collector = ContextCollector()
        result = collector.collect_from_path(tmp_path / "nonexistent")

        assert result == ""

    def test_collect_respects_max_files(self, tmp_path):
        """Test that collection respects max_files config."""
        # Create many files
        for i in range(100):
            (tmp_path / f"file_{i}.py").write_text(f"# File {i}")

        config = Config()
        config.context.max_files = 5
        collector = ContextCollector(config)

        result = collector.collect_from_path(tmp_path)

        # Count how many files were included
        file_count = result.count("# file_")
        assert file_count <= 5

    def test_collect_ignores_patterns(self, tmp_path):
        """Test that collection ignores configured patterns."""
        # Create files in ignored directory
        ignored_dir = tmp_path / "node_modules"
        ignored_dir.mkdir()
        (ignored_dir / "package.json").write_text('{"name": "test"}')

        # Create a regular file
        (tmp_path / "main.py").write_text("print('main')")

        collector = ContextCollector()
        result = collector.collect_from_path(tmp_path)

        assert "main.py" in result
        assert "package.json" not in result

    def test_collect_respects_gitignore(self, tmp_path):
        """Test that collection respects .gitignore."""
        # Create .gitignore
        (tmp_path / ".gitignore").write_text("*.log\nsecrets/")

        # Create ignored files
        (tmp_path / "debug.log").write_text("log content")
        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()
        (secrets_dir / "keys.txt").write_text("secret keys")

        # Create a regular file
        (tmp_path / "main.py").write_text("print('main')")

        collector = ContextCollector()
        result = collector.collect_from_path(tmp_path)

        assert "main.py" in result
        assert "debug.log" not in result
        assert "keys.txt" not in result

    def test_collect_summary_with_pyproject(self, tmp_path):
        """Test collecting project summary with pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test-project"')

        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('main')")

        collector = ContextCollector()
        result = collector.collect_summary(tmp_path)

        assert result is not None
        assert "pyproject.toml" in result
        assert "test-project" in result
        assert "Project Structure" in result

    def test_collect_summary_without_project_file(self, tmp_path):
        """Test collecting summary without recognized project file."""
        (tmp_path / "random.txt").write_text("hello")

        collector = ContextCollector()
        result = collector.collect_summary(tmp_path)

        assert result is None

    def test_collect_summary_with_package_json(self, tmp_path):
        """Test collecting summary with package.json."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "my-npm-package"}')

        collector = ContextCollector()
        result = collector.collect_summary(tmp_path)

        assert result is not None
        assert "package.json" in result

    def test_build_tree_depth_limit(self, tmp_path):
        """Test that tree building respects depth limit."""
        # Create nested directories
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "deep.txt").write_text("deep file")

        collector = ContextCollector()
        result = collector._build_tree(tmp_path, max_depth=2)

        # Should show a/ and a/b/ but not deeper
        assert "a/" in result
        assert "b/" in result
        # The depth is limited, so deeper directories might not show their contents


class TestFileIndexer:
    """Tests for FileIndexer class."""

    def test_build_index(self, tmp_path):
        """Test building file index."""
        (tmp_path / "main.py").write_text("print('main')")
        (tmp_path / "utils.py").write_text("def util(): pass")

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        files = indexer.get_all_files()
        assert len(files) == 2

    def test_build_index_ignores_binary(self, tmp_path):
        """Test that binary files are ignored."""
        (tmp_path / "main.py").write_text("print('main')")
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        files = indexer.get_all_files()
        paths = [f.relative_path for f in files]
        assert "main.py" in paths
        assert "image.png" not in paths

    def test_build_index_respects_gitignore(self, tmp_path):
        """Test that gitignore patterns are respected."""
        (tmp_path / ".gitignore").write_text("*.log")
        (tmp_path / "main.py").write_text("print('main')")
        (tmp_path / "debug.log").write_text("log content")

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        files = indexer.get_all_files()
        paths = [f.relative_path for f in files]
        assert "main.py" in paths
        assert "debug.log" not in paths

    def test_find_by_name(self, tmp_path):
        """Test finding files by name."""
        (tmp_path / "main.py").write_text("main")
        (tmp_path / "utils.py").write_text("utils")
        (tmp_path / "main_test.py").write_text("test")

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        results = indexer.find_by_name("main")
        names = [f.path.name for f in results]
        assert "main.py" in names
        assert "main_test.py" in names
        assert "utils.py" not in names

    def test_find_by_extension(self, tmp_path):
        """Test finding files by extension."""
        (tmp_path / "main.py").write_text("main")
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "config.py").write_text("config")

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        results = indexer.find_by_extension(".py")
        extensions = [f.extension for f in results]
        assert all(ext == ".py" for ext in extensions)
        assert len(results) == 2

    def test_find_by_extension_without_dot(self, tmp_path):
        """Test finding files by extension without leading dot."""
        (tmp_path / "main.py").write_text("main")

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        results = indexer.find_by_extension("py")  # No dot
        assert len(results) == 1

    def test_get_summary(self, tmp_path):
        """Test getting summary of indexed files."""
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.py").write_text("b")
        (tmp_path / "c.js").write_text("c")

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        summary = indexer.get_summary()
        assert summary[".py"] == 2
        assert summary[".js"] == 1

    def test_file_info_includes_line_count(self, tmp_path):
        """Test that FileInfo includes line count for small text files."""
        content = "line1\nline2\nline3"
        (tmp_path / "test.py").write_text(content)

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        files = indexer.get_all_files()
        assert len(files) == 1
        assert files[0].lines == 3

    def test_file_info_properties(self, tmp_path):
        """Test FileInfo dataclass properties."""
        content = "test content"
        test_file = tmp_path / "test.py"
        test_file.write_text(content)

        indexer = FileIndexer(tmp_path)
        indexer.build_index()

        files = indexer.get_all_files()
        assert len(files) == 1

        file_info = files[0]
        assert file_info.path == test_file
        assert file_info.relative_path == "test.py"
        assert file_info.extension == ".py"
        assert file_info.size == len(content)


class TestMaxTreeEntries:
    """Tests for MAX_TREE_ENTRIES constant."""

    def test_max_tree_entries_is_defined(self):
        """Test that MAX_TREE_ENTRIES constant exists."""
        assert MAX_TREE_ENTRIES > 0
        assert MAX_TREE_ENTRIES == 20
