"""Tests for AI providers."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from flow.providers import get_provider, AnthropicProvider, OllamaProvider
from flow.providers.base import Provider, GenerationResult
from flow.config import Config, ProviderConfig


class TestProviderBase:
    """Tests for the Provider base class."""

    def test_generation_result_creation(self):
        """Test GenerationResult dataclass."""
        result = GenerationResult(
            content="test content",
            model="test-model",
            usage={"input_tokens": 10, "output_tokens": 20},
        )
        assert result.content == "test content"
        assert result.model == "test-model"
        assert result.usage == {"input_tokens": 10, "output_tokens": 20}

    def test_generation_result_without_usage(self):
        """Test GenerationResult without usage data."""
        result = GenerationResult(content="test", model="model")
        assert result.usage is None


class TestGetProvider:
    """Tests for the get_provider factory function."""

    def test_get_anthropic_provider(self):
        """Test getting Anthropic provider."""
        config = Config(provider="anthropic")
        provider = get_provider(config)
        assert isinstance(provider, AnthropicProvider)
        assert provider.name == "anthropic"

    def test_get_ollama_provider(self):
        """Test getting Ollama provider."""
        config = Config(provider="ollama")
        provider = get_provider(config)
        assert isinstance(provider, OllamaProvider)
        assert provider.name == "ollama"

    def test_get_unknown_provider(self):
        """Test that unknown provider raises ValueError."""
        config = Config(provider="unknown")
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider(config)


class TestAnthropicProvider:
    """Tests for the Anthropic provider."""

    def test_provider_name(self):
        """Test provider name property."""
        config = Config()
        provider = AnthropicProvider(config)
        assert provider.name == "anthropic"

    def test_is_available_with_api_key(self):
        """Test is_available returns True with API key."""
        config = Config()
        config.anthropic.api_key = "test-key"
        provider = AnthropicProvider(config)
        
        with patch("flow.providers.anthropic.auth.get_access_token", return_value=None):
            assert provider.is_available() is True

    def test_is_available_with_oauth(self):
        """Test is_available returns True with OAuth token."""
        config = Config()
        provider = AnthropicProvider(config)
        
        with patch("flow.providers.anthropic.auth.get_access_token", return_value="oauth-token"):
            assert provider.is_available() is True

    def test_is_available_without_credentials(self):
        """Test is_available returns False without credentials."""
        config = Config()
        config.anthropic.api_key = None
        provider = AnthropicProvider(config)
        
        with patch("flow.providers.anthropic.auth.get_access_token", return_value=None):
            assert provider.is_available() is False

    @patch("flow.providers.anthropic.anthropic.Anthropic")
    @patch("flow.providers.anthropic.auth.get_access_token")
    def test_generate_with_oauth(self, mock_get_token, mock_anthropic_class):
        """Test generate using OAuth authentication."""
        mock_get_token.return_value = "oauth-token"
        
        # Mock the Anthropic client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock the response
        mock_response = Mock()
        mock_response.content = [Mock(type="text", text="Generated code")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage = Mock(input_tokens=10, output_tokens=20)
        mock_client.messages.create.return_value = mock_response
        
        config = Config()
        provider = AnthropicProvider(config)
        result = provider.generate(prompt="Write a function")
        
        assert result.content == "Generated code"
        assert result.model == "claude-sonnet-4-20250514"
        assert result.usage == {"input_tokens": 10, "output_tokens": 20}

    @patch("flow.providers.anthropic.anthropic.Anthropic")
    @patch("flow.providers.anthropic.auth.get_access_token")
    def test_generate_with_context(self, mock_get_token, mock_anthropic_class):
        """Test generate with context included."""
        mock_get_token.return_value = "oauth-token"
        
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(type="text", text="Generated")]
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.usage = Mock(input_tokens=10, output_tokens=20)
        mock_client.messages.create.return_value = mock_response
        
        config = Config()
        provider = AnthropicProvider(config)
        result = provider.generate(
            prompt="Write a function",
            context="def existing_function(): pass",
        )
        
        # Verify context was included in the message
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert "<context>" in messages[0]["content"]
        assert "existing_function" in messages[0]["content"]


class TestOllamaProvider:
    """Tests for the Ollama provider."""

    def test_provider_name(self):
        """Test provider name property."""
        config = Config()
        provider = OllamaProvider(config)
        assert provider.name == "ollama"

    def test_default_host_and_model(self):
        """Test default host and model configuration."""
        config = Config()
        provider = OllamaProvider(config)
        assert provider._host == "http://localhost:11434"
        assert provider._model == "codellama"

    def test_custom_host_and_model(self):
        """Test custom host and model configuration."""
        config = Config()
        config.ollama.host = "http://custom:8080"
        config.ollama.model = "llama2"
        provider = OllamaProvider(config)
        assert provider._host == "http://custom:8080"
        assert provider._model == "llama2"

    @patch("flow.providers.ollama.httpx.get")
    def test_is_available_when_running(self, mock_get):
        """Test is_available returns True when Ollama is running."""
        mock_get.return_value = Mock(status_code=200)
        
        config = Config()
        provider = OllamaProvider(config)
        assert provider.is_available() is True
        
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            timeout=5.0
        )

    @patch("flow.providers.ollama.httpx.get")
    def test_is_available_when_not_running(self, mock_get):
        """Test is_available returns False when Ollama is not running."""
        mock_get.side_effect = Exception("Connection refused")
        
        config = Config()
        provider = OllamaProvider(config)
        assert provider.is_available() is False

    @patch("flow.providers.ollama.httpx.post")
    def test_generate(self, mock_post):
        """Test generate method."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Generated code here",
            "prompt_eval_count": 10,
            "eval_count": 20,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        config = Config()
        provider = OllamaProvider(config)
        result = provider.generate(prompt="Write a function")
        
        assert result.content == "Generated code here"
        assert result.model == "codellama"
        assert result.usage == {"prompt_tokens": 10, "completion_tokens": 20}

    @patch("flow.providers.ollama.httpx.post")
    def test_generate_with_system_prompt(self, mock_post):
        """Test generate with system prompt."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "OK", "prompt_eval_count": 5, "eval_count": 10}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        config = Config()
        provider = OllamaProvider(config)
        provider.generate(
            prompt="Write a function",
            system="You are a helpful assistant",
        )
        
        # Verify system prompt was included
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert payload["system"] == "You are a helpful assistant"

    @patch("flow.providers.ollama.httpx.post")
    def test_generate_with_context(self, mock_post):
        """Test generate with context."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "OK", "prompt_eval_count": 5, "eval_count": 10}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        config = Config()
        provider = OllamaProvider(config)
        provider.generate(
            prompt="Explain this",
            context="def foo(): pass",
        )
        
        # Verify context was included in prompt
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert "<context>" in payload["prompt"]
        assert "def foo(): pass" in payload["prompt"]
