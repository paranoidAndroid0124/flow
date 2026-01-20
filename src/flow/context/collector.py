"""Context collection for codebase understanding."""

from pathlib import Path

import pathspec

from flow.config import Config
from flow.utils.files import is_binary_file, read_file_safe, get_language_from_extension


class ContextCollector:
    """Collects and formats context from the codebase."""

    def __init__(self, config: Config | None = None):
        """Initialize the context collector.

        Args:
            config: Configuration object. If None, loads from default config.
        """
        self.config = config or Config.load()
        self._ignore_patterns = self.config.context.ignore
        self._max_files = self.config.context.max_files

    def collect_from_path(self, path: Path) -> str:
        """Collect context from a file or directory.

        Args:
            path: Path to collect context from

        Returns:
            Formatted context string
        """
        if path.is_file():
            return self._format_file(path)
        elif path.is_dir():
            return self._collect_directory(path)
        else:
            return ""

    def collect_summary(self, root: Path | None = None) -> str | None:
        """Collect a summary of the project structure.

        Args:
            root: Root directory (defaults to cwd)

        Returns:
            Summary string or None if not in a project
        """
        root = root or Path.cwd()

        # Check if we're in a recognizable project
        project_files = [
            "pyproject.toml", "package.json", "Cargo.toml",
            "go.mod", "pom.xml", "build.gradle",
        ]

        project_file = None
        for pf in project_files:
            if (root / pf).exists():
                project_file = root / pf
                break

        if not project_file:
            return None

        # Build a summary
        parts = []

        # Include project file
        content = read_file_safe(project_file)
        if content:
            lang = get_language_from_extension(project_file)
            parts.append(f"# {project_file.name}\n```{lang}\n{content}\n```")

        # Include directory structure (limited)
        tree = self._build_tree(root, max_depth=2)
        if tree:
            parts.append(f"# Project Structure\n```\n{tree}\n```")

        return "\n\n".join(parts) if parts else None

    def _collect_directory(self, path: Path) -> str:
        """Collect context from a directory.

        Args:
            path: Directory path

        Returns:
            Formatted context string
        """
        files = self._find_files(path)
        parts = []

        for file_path in files[:self._max_files]:
            formatted = self._format_file(file_path)
            if formatted:
                parts.append(formatted)

        return "\n\n".join(parts)

    def _find_files(self, path: Path) -> list[Path]:
        """Find all relevant files in a directory.

        Args:
            path: Directory to search

        Returns:
            List of file paths
        """
        # Load gitignore if present
        gitignore_path = path / ".gitignore"
        spec = None
        if gitignore_path.exists():
            patterns = gitignore_path.read_text().splitlines()
            patterns.extend(self._ignore_patterns)
            spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        else:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", self._ignore_patterns)

        files = []
        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue
            if is_binary_file(file_path):
                continue

            # Check against ignore patterns
            rel_path = file_path.relative_to(path)
            if spec and spec.match_file(str(rel_path)):
                continue

            files.append(file_path)

        # Sort by modification time (most recent first)
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def _format_file(self, path: Path) -> str:
        """Format a file for context.

        Args:
            path: File path

        Returns:
            Formatted file content
        """
        content = read_file_safe(path)
        if not content:
            return ""

        lang = get_language_from_extension(path)
        return f"# {path.name}\n```{lang}\n{content}\n```"

    def _build_tree(self, path: Path, max_depth: int = 3, prefix: str = "") -> str:
        """Build a simple directory tree representation.

        Args:
            path: Root path
            max_depth: Maximum depth to traverse
            prefix: Current line prefix

        Returns:
            Tree string representation
        """
        if max_depth <= 0:
            return ""

        lines = []
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return ""

        # Filter out ignored directories
        entries = [
            e for e in entries
            if e.name not in self._ignore_patterns
        ]

        for i, entry in enumerate(entries[:20]):  # Limit entries
            is_last = i == len(entries) - 1 or i == 19
            connector = "└── " if is_last else "├── "

            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                extension = "    " if is_last else "│   "
                subtree = self._build_tree(entry, max_depth - 1, prefix + extension)
                if subtree:
                    lines.append(subtree)
            else:
                lines.append(f"{prefix}{connector}{entry.name}")

        return "\n".join(lines)
