"""File utilities."""

from pathlib import Path


# Common binary file extensions to skip
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".class", ".o",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".db", ".sqlite", ".sqlite3",
}

# Common text file extensions
TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
    ".java", ".kt", ".scala",
    ".c", ".cpp", ".h", ".hpp", ".cc",
    ".go", ".rs", ".swift",
    ".rb", ".php", ".pl", ".pm",
    ".sh", ".bash", ".zsh", ".fish",
    ".html", ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml", ".xml",
    ".md", ".txt", ".rst", ".org",
    ".sql", ".graphql",
    ".dockerfile", ".env", ".gitignore",
    ".conf", ".cfg", ".ini",
}


def is_binary_file(path: Path) -> bool:
    """Check if a file is likely binary based on extension."""
    return path.suffix.lower() in BINARY_EXTENSIONS


def is_text_file(path: Path) -> bool:
    """Check if a file is likely a text file based on extension."""
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return True
    # Files without extension might be text (e.g., Makefile, Dockerfile)
    if not suffix and path.name in {"Makefile", "Dockerfile", "Vagrantfile", "Jenkinsfile"}:
        return True
    return False


def read_file_safe(path: Path, max_size: int = 100_000) -> str | None:
    """Read a file safely, returning None if it can't be read or is too large.

    Args:
        path: Path to the file
        max_size: Maximum file size in bytes

    Returns:
        File contents or None if unable to read
    """
    try:
        if path.stat().st_size > max_size:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def get_language_from_extension(path: Path) -> str:
    """Get the programming language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "jsx",
        ".tsx": "tsx",
        ".java": "java",
        ".kt": "kotlin",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".sh": "bash",
        ".bash": "bash",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".xml": "xml",
        ".sql": "sql",
        ".md": "markdown",
    }
    return ext_map.get(path.suffix.lower(), "text")
