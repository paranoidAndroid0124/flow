"""AI provider implementations."""

from flow.providers.base import Provider, GenerationResult
from flow.providers.anthropic import AnthropicProvider
from flow.providers.ollama import OllamaProvider
from flow.config import Config


def get_provider(config: Config | None = None) -> Provider:
    """Get the configured AI provider.

    Args:
        config: Optional configuration. If None, loads from default config.

    Returns:
        The configured Provider instance.

    Raises:
        ValueError: If the configured provider is unknown.
    """
    cfg = config or Config.load()

    if cfg.provider == "anthropic":
        return AnthropicProvider(cfg)
    elif cfg.provider == "ollama":
        return OllamaProvider(cfg)
    else:
        raise ValueError(f"Unknown provider: {cfg.provider}")


__all__ = ["Provider", "GenerationResult", "AnthropicProvider", "OllamaProvider", "get_provider"]
