"""Anthropic Claude provider implementation."""

import anthropic

from flow.providers.base import Provider, GenerationResult
from flow.config import Config


class AnthropicProvider(Provider):
    """Provider implementation for Anthropic's Claude models."""

    def __init__(self, config: Config | None = None):
        """Initialize the Anthropic provider.

        Args:
            config: Configuration object. If None, loads from default config.
        """
        self.config = config or Config.load()
        self._client: anthropic.Anthropic | None = None
        self._model = self.config.model

    @property
    def client(self) -> anthropic.Anthropic:
        """Get or create the Anthropic client."""
        if self._client is None:
            api_key = self.config.anthropic.api_key
            if not api_key:
                raise ValueError(
                    "Anthropic API key not configured. "
                    "Set ANTHROPIC_API_KEY environment variable or run 'flow config set anthropic.api_key YOUR_KEY'"
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    @property
    def name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        """Check if the Anthropic provider is available."""
        try:
            return self.config.anthropic.api_key is not None
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        context: str | None = None,
        max_tokens: int = 4096,
    ) -> GenerationResult:
        """Generate a response using Claude.

        Args:
            prompt: The user's prompt/request
            system: Optional system prompt
            context: Optional context (e.g., code files)
            max_tokens: Maximum tokens in response

        Returns:
            GenerationResult with the generated content
        """
        messages = []

        # Build the user message with optional context
        user_content = prompt
        if context:
            user_content = f"<context>\n{context}\n</context>\n\n{prompt}"

        messages.append({"role": "user", "content": user_content})

        # Build request kwargs
        kwargs: dict = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        # Extract text content
        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return GenerationResult(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
