"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    """A message in a conversation."""

    role: str  # "user" or "assistant"
    content: str


@dataclass
class GenerationResult:
    """Result from an AI generation request."""

    content: str
    model: str
    usage: dict[str, int] | None = None


class Provider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: str | None = None,
        context: str | None = None,
        max_tokens: int = 4096,
    ) -> GenerationResult:
        """Generate a response from the AI model.

        Args:
            prompt: The user's prompt/request
            system: Optional system prompt
            context: Optional context (e.g., code files)
            max_tokens: Maximum tokens in response

        Returns:
            GenerationResult with the generated content
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """The provider's name."""
        pass
