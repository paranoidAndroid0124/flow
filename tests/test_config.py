"""Tests for configuration management."""

import os
from pathlib import Path
import tempfile

import pytest

from flow.config import Config, ProviderConfig, ContextConfig


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    assert config.provider == "anthropic"
    assert config.model == "claude-sonnet-4-20250514"
    assert config.context.max_files == 50


def test_config_from_dict():
    """Test creating config from dictionary."""
    data = {
        "default": {
            "provider": "ollama",
            "model": "codellama",
        },
        "ollama": {
            "host": "http://localhost:11434",
            "model": "deepseek-coder",
        },
        "context": {
            "max_files": 100,
            "ignore": [".git", "node_modules"],
        },
    }

    config = Config.from_dict(data)
    assert config.provider == "ollama"
    assert config.model == "codellama"
    assert config.ollama.host == "http://localhost:11434"
    assert config.ollama.model == "deepseek-coder"
    assert config.context.max_files == 100


def test_resolve_env_var():
    """Test environment variable resolution."""
    # Set a test env var
    os.environ["TEST_API_KEY"] = "test-key-123"

    try:
        result = Config._resolve_env_var("${TEST_API_KEY}")
        assert result == "test-key-123"

        # Test non-env var
        result = Config._resolve_env_var("plain-value")
        assert result == "plain-value"

        # Test None
        result = Config._resolve_env_var(None)
        assert result is None
    finally:
        del os.environ["TEST_API_KEY"]


def test_get_provider_config():
    """Test getting provider-specific config."""
    config = Config()

    config.provider = "anthropic"
    provider_config = config.get_provider_config()
    assert provider_config.name == "anthropic"

    config.provider = "ollama"
    provider_config = config.get_provider_config()
    assert provider_config.name == "ollama"
