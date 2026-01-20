"""Ollama provider implementation."""

import logging

import httpx

from flow.providers.base import Provider, GenerationResult
from flow.config import Config

logger = logging.getLogger(__name__)


class OllamaProvider(Provider):
    """Provider implementation for local Ollama models."""

    def __init__(self, config: Config | None = None):
        """Initialize the Ollama provider.

        Args:
            config: Configuration object. If None, loads from default config.
        """
        self.config = config or Config.load()
        self._host = self.config.ollama.host or "http://localhost:11434"
        self._model = self.config.ollama.model or "codellama"

    @property
    def name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        """Check if Ollama is running and available."""
        try:
            response = httpx.get(f"{self._host}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        context: str | None = None,
        max_tokens: int = 4096,
    ) -> GenerationResult:
        """Generate a response using Ollama.

        Args:
            prompt: The user's prompt/request
            system: Optional system prompt
            context: Optional context (e.g., code files)
            max_tokens: Maximum tokens in response

        Returns:
            GenerationResult with the generated content
        """
        # Build the prompt with optional context
        full_prompt = prompt
        if context:
            full_prompt = f"<context>\n{context}\n</context>\n\n{prompt}"

        # Build request payload
        payload = {
            "model": self._model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
            },
        }

        if system:
            payload["system"] = system

        response = httpx.post(
            f"{self._host}/api/generate",
            json=payload,
            timeout=120.0,  # Longer timeout for generation
        )
        response.raise_for_status()
        data = response.json()

        return GenerationResult(
            content=data.get("response", ""),
            model=self._model,
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            },
        )
