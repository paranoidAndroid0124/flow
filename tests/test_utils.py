"""Tests for utility functions."""

from pathlib import Path
import tempfile

from flow.utils.files import (
    is_binary_file,
    is_text_file,
    read_file_safe,
    get_language_from_extension,
)


def test_is_binary_file():
    """Test binary file detection."""
    assert is_binary_file(Path("image.png")) is True
    assert is_binary_file(Path("archive.zip")) is True
    assert is_binary_file(Path("script.py")) is False
    assert is_binary_file(Path("data.json")) is False


def test_is_text_file():
    """Test text file detection."""
    assert is_text_file(Path("script.py")) is True
    assert is_text_file(Path("index.html")) is True
    assert is_text_file(Path("config.yaml")) is True
    assert is_text_file(Path("Makefile")) is True
    assert is_text_file(Path("unknown.xyz")) is False


def test_get_language_from_extension():
    """Test language detection from extension."""
    assert get_language_from_extension(Path("main.py")) == "python"
    assert get_language_from_extension(Path("app.js")) == "javascript"
    assert get_language_from_extension(Path("index.ts")) == "typescript"
    assert get_language_from_extension(Path("main.go")) == "go"
    assert get_language_from_extension(Path("lib.rs")) == "rust"
    assert get_language_from_extension(Path("unknown.xyz")) == "text"


def test_read_file_safe():
    """Test safe file reading."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test content")
        temp_path = Path(f.name)

    try:
        content = read_file_safe(temp_path)
        assert content == "test content"

        # Test non-existent file
        content = read_file_safe(Path("/nonexistent/file.txt"))
        assert content is None
    finally:
        temp_path.unlink()
