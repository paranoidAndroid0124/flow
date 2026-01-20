"""Simple file indexing for the codebase."""

from pathlib import Path
from dataclasses import dataclass

import pathspec

from flow.config import Config
from flow.utils.files import is_binary_file, is_text_file


@dataclass
class FileInfo:
    """Information about an indexed file."""

    path: Path
    relative_path: str
    extension: str
    size: int
    lines: int | None = None


class FileIndexer:
    """Indexes files in a codebase for quick lookup."""

    def __init__(self, root: Path | None = None, config: Config | None = None):
        """Initialize the file indexer.

        Args:
            root: Root directory to index (defaults to cwd)
            config: Configuration object
        """
        self.root = root or Path.cwd()
        self.config = config or Config.load()
        self._ignore_patterns = self.config.context.ignore
        self._index: dict[str, FileInfo] = {}

    def build_index(self) -> None:
        """Build the file index."""
        self._index.clear()

        # Load gitignore if present
        gitignore_path = self.root / ".gitignore"
        patterns = list(self._ignore_patterns)
        if gitignore_path.exists():
            patterns.extend(gitignore_path.read_text().splitlines())

        spec = pathspec.PathSpec.from_lines("gitignore", patterns)

        for file_path in self.root.rglob("*"):
            if not file_path.is_file():
                continue
            if is_binary_file(file_path):
                continue

            rel_path = file_path.relative_to(self.root)
            if spec.match_file(str(rel_path)):
                continue

            info = self._create_file_info(file_path, rel_path)
            self._index[str(rel_path)] = info

    def _create_file_info(self, path: Path, rel_path: Path) -> FileInfo:
        """Create FileInfo for a file.

        Args:
            path: Absolute path
            rel_path: Relative path from root

        Returns:
            FileInfo object
        """
        stat = path.stat()
        lines = None

        # Count lines for text files (if small enough)
        if is_text_file(path) and stat.st_size < 100_000:
            try:
                lines = len(path.read_text().splitlines())
            except Exception:
                pass

        return FileInfo(
            path=path,
            relative_path=str(rel_path),
            extension=path.suffix.lower(),
            size=stat.st_size,
            lines=lines,
        )

    def find_by_name(self, name: str) -> list[FileInfo]:
        """Find files by name (partial match).

        Args:
            name: File name or partial name to search

        Returns:
            List of matching FileInfo objects
        """
        name_lower = name.lower()
        return [
            info for info in self._index.values()
            if name_lower in info.path.name.lower()
        ]

    def find_by_extension(self, extension: str) -> list[FileInfo]:
        """Find files by extension.

        Args:
            extension: File extension (with or without dot)

        Returns:
            List of matching FileInfo objects
        """
        ext = extension if extension.startswith(".") else f".{extension}"
        ext = ext.lower()
        return [
            info for info in self._index.values()
            if info.extension == ext
        ]

    def get_all_files(self) -> list[FileInfo]:
        """Get all indexed files.

        Returns:
            List of all FileInfo objects
        """
        return list(self._index.values())

    def get_summary(self) -> dict[str, int]:
        """Get a summary of the indexed files.

        Returns:
            Dictionary with extension counts
        """
        summary: dict[str, int] = {}
        for info in self._index.values():
            ext = info.extension or "(no extension)"
            summary[ext] = summary.get(ext, 0) + 1
        return dict(sorted(summary.items(), key=lambda x: -x[1]))
