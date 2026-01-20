"""Utility functions."""

from flow.utils.files import (
    is_binary_file,
    is_text_file,
    read_file_safe,
    get_language_from_extension,
)

__all__ = [
    "is_binary_file",
    "is_text_file",
    "read_file_safe",
    "get_language_from_extension",
]
