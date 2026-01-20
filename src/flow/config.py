"""Configuration management for Flow."""

import logging
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

logger = logging.getLogger(__name__)


CONFIG_DIR = Path.home() / ".config" / "flow"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "default": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
    },
    "anthropic": {
        "api_key": "${ANTHROPIC_API_KEY}",
    },
    "ollama": {
        "host": "http://localhost:11434",
        "model": "codellama",
    },
    "jira": {
        "url": "${JIRA_URL}",
        "email": "${JIRA_EMAIL}",
        "api_token": "${JIRA_API_TOKEN}",
        "default_project": "",
    },
    "context": {
        "max_files": 50,
        "ignore": [".git", "node_modules", "__pycache__", ".venv", "dist", "build"],
    },
}


@dataclass
class ProviderConfig:
    """Configuration for a specific provider."""

    name: str
    api_key: str | None = None
    host: str | None = None
    model: str | None = None


@dataclass
class JiraConfig:
    """Configuration for Jira integration."""

    url: str | None = None
    email: str | None = None
    api_token: str | None = None
    default_project: str | None = None

    @property
    def is_configured(self) -> bool:
        """Check if Jira is configured."""
        return all([self.url, self.email, self.api_token])


@dataclass
class ContextConfig:
    """Configuration for context collection."""

    max_files: int = 50
    ignore: list[str] = field(default_factory=lambda: [".git", "node_modules", "__pycache__", ".venv"])


@dataclass
class Config:
    """Main configuration class."""

    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    anthropic: ProviderConfig = field(default_factory=lambda: ProviderConfig(name="anthropic"))
    ollama: ProviderConfig = field(default_factory=lambda: ProviderConfig(name="ollama"))
    jira: JiraConfig = field(default_factory=JiraConfig)
    context: ContextConfig = field(default_factory=ContextConfig)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file."""
        if not CONFIG_FILE.exists():
            return cls()

        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        default = data.get("default", {})

        # Parse anthropic config
        anthropic_data = data.get("anthropic", {})
        anthropic = ProviderConfig(
            name="anthropic",
            api_key=cls._resolve_env_var(anthropic_data.get("api_key")),
            model=anthropic_data.get("model"),
        )

        # Parse ollama config
        ollama_data = data.get("ollama", {})
        ollama = ProviderConfig(
            name="ollama",
            host=ollama_data.get("host", "http://localhost:11434"),
            model=ollama_data.get("model", "codellama"),
        )

        # Parse jira config
        jira_data = data.get("jira", {})
        jira = JiraConfig(
            url=cls._resolve_env_var(jira_data.get("url")),
            email=cls._resolve_env_var(jira_data.get("email")),
            api_token=cls._resolve_env_var(jira_data.get("api_token")),
            default_project=jira_data.get("default_project"),
        )

        # Parse context config
        context_data = data.get("context", {})
        context = ContextConfig(
            max_files=context_data.get("max_files", 50),
            ignore=context_data.get("ignore", [".git", "node_modules", "__pycache__", ".venv"]),
        )

        return cls(
            provider=default.get("provider", "anthropic"),
            model=default.get("model", "claude-sonnet-4-20250514"),
            anthropic=anthropic,
            ollama=ollama,
            jira=jira,
            context=context,
        )

    @staticmethod
    def _resolve_env_var(value: str | None) -> str | None:
        """Resolve environment variable references like ${VAR_NAME}."""
        if value is None:
            return None
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var)
        return value

    def get_provider_config(self) -> ProviderConfig:
        """Get the configuration for the current provider."""
        if self.provider == "anthropic":
            return self.anthropic
        elif self.provider == "ollama":
            return self.ollama
        else:
            raise ValueError(f"Unknown provider: {self.provider}")


def init_config() -> Path:
    """Initialize configuration file with defaults."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(DEFAULT_CONFIG, f)

    return CONFIG_FILE


def get_config() -> Config:
    """Get the current configuration."""
    return Config.load()


def set_config_value(key: str, value: str) -> None:
    """Set a configuration value.

    Key format: "section.key" (e.g., "default.provider" or "anthropic.api_key")
    """
    if not CONFIG_FILE.exists():
        init_config()

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    parts = key.split(".")
    if len(parts) != 2:
        raise ValueError("Key must be in format 'section.key'")

    section, key_name = parts

    if section not in data:
        data[section] = {}

    # Try to convert to appropriate type
    if value.lower() == "true":
        data[section][key_name] = True
    elif value.lower() == "false":
        data[section][key_name] = False
    elif value.isdigit():
        data[section][key_name] = int(value)
    else:
        data[section][key_name] = value

    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)
