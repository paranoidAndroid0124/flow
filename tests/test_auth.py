"""Tests for OAuth authentication module."""

import json
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import httpx

from flow.auth import (
    generate_pkce,
    get_authorization_url,
    exchange_code,
    refresh_tokens,
    save_tokens,
    load_tokens,
    delete_tokens,
    get_access_token,
    is_authenticated,
    login,
    complete_login,
    TokenData,
    CLIENT_ID,
    AUTHORIZATION_URL,
    REDIRECT_URI,
    SCOPES,
)


class TestPKCE:
    """Tests for PKCE generation."""

    def test_generate_pkce_returns_tuple(self):
        """Test that generate_pkce returns a tuple of two strings."""
        verifier, challenge = generate_pkce()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)

    def test_generate_pkce_verifier_length(self):
        """Test that code verifier has appropriate length."""
        verifier, _ = generate_pkce()
        # URL-safe base64 of 32 bytes = 43 characters
        assert len(verifier) >= 43

    def test_generate_pkce_challenge_is_base64(self):
        """Test that code challenge is valid base64."""
        _, challenge = generate_pkce()
        # Should only contain URL-safe base64 characters
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in valid_chars for c in challenge)

    def test_generate_pkce_unique_values(self):
        """Test that each call generates unique values."""
        verifier1, challenge1 = generate_pkce()
        verifier2, challenge2 = generate_pkce()
        assert verifier1 != verifier2
        assert challenge1 != challenge2


class TestAuthorizationURL:
    """Tests for authorization URL generation."""

    def test_get_authorization_url_format(self):
        """Test authorization URL has correct format."""
        url = get_authorization_url("test-state", "test-challenge")
        assert url.startswith(AUTHORIZATION_URL)
        assert "response_type=code" in url
        assert f"client_id={CLIENT_ID}" in url
        assert "test-state" in url
        assert "test-challenge" in url
        assert "code_challenge_method=S256" in url

    def test_get_authorization_url_scopes(self):
        """Test authorization URL includes all scopes."""
        url = get_authorization_url("state", "challenge")
        # Scopes should be URL-encoded
        for scope in SCOPES:
            # Colons are encoded as %3A in URLs
            encoded_scope = scope.replace(":", "%3A")
            assert scope in url or encoded_scope in url


class TestTokenData:
    """Tests for TokenData dataclass."""

    def test_token_data_creation(self):
        """Test TokenData creation."""
        token = TokenData(
            access_token="access",
            refresh_token="refresh",
            expires_at=1234567890.0,
        )
        assert token.access_token == "access"
        assert token.refresh_token == "refresh"
        assert token.expires_at == 1234567890.0


class TestTokenStorage:
    """Tests for token storage functions."""

    def test_save_and_load_tokens(self, tmp_path, monkeypatch):
        """Test saving and loading tokens."""
        auth_file = tmp_path / "auth.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)
        monkeypatch.setattr("flow.auth.AUTH_DIR", tmp_path)

        token_data = TokenData(
            access_token="test-access",
            refresh_token="test-refresh",
            expires_at=time.time() + 3600,
        )

        save_tokens(token_data)
        loaded = load_tokens()

        assert loaded is not None
        assert loaded.access_token == "test-access"
        assert loaded.refresh_token == "test-refresh"

    def test_load_tokens_nonexistent(self, tmp_path, monkeypatch):
        """Test loading tokens when file doesn't exist."""
        auth_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)

        result = load_tokens()
        assert result is None

    def test_load_tokens_invalid_json(self, tmp_path, monkeypatch):
        """Test loading tokens with invalid JSON."""
        auth_file = tmp_path / "auth.json"
        auth_file.write_text("invalid json")
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)

        result = load_tokens()
        assert result is None

    def test_load_tokens_missing_keys(self, tmp_path, monkeypatch):
        """Test loading tokens with missing keys."""
        auth_file = tmp_path / "auth.json"
        auth_file.write_text('{"access_token": "test"}')  # Missing other keys
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)

        result = load_tokens()
        assert result is None

    def test_delete_tokens(self, tmp_path, monkeypatch):
        """Test deleting tokens."""
        auth_file = tmp_path / "auth.json"
        auth_file.write_text('{"test": "data"}')
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)

        result = delete_tokens()
        assert result is True
        assert not auth_file.exists()

    def test_delete_tokens_nonexistent(self, tmp_path, monkeypatch):
        """Test deleting tokens when file doesn't exist."""
        auth_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)

        result = delete_tokens()
        assert result is False

    def test_save_tokens_sets_permissions(self, tmp_path, monkeypatch):
        """Test that saved tokens have restrictive permissions."""
        auth_file = tmp_path / "auth.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)
        monkeypatch.setattr("flow.auth.AUTH_DIR", tmp_path)

        token_data = TokenData(
            access_token="test",
            refresh_token="test",
            expires_at=time.time() + 3600,
        )

        save_tokens(token_data)

        # Check file permissions (0o600 = owner read/write only)
        mode = auth_file.stat().st_mode & 0o777
        assert mode == 0o600


class TestExchangeCode:
    """Tests for authorization code exchange."""

    @patch("flow.auth.httpx.Client")
    def test_exchange_code_success(self, mock_client_class):
        """Test successful code exchange."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        result = exchange_code("auth-code", "verifier")

        assert result.access_token == "new-access"
        assert result.refresh_token == "new-refresh"
        assert result.expires_at > time.time()

    @patch("flow.auth.httpx.Client")
    def test_exchange_code_http_error(self, mock_client_class):
        """Test code exchange with HTTP error."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=Mock(status_code=400)
        )
        mock_client.post.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            exchange_code("auth-code", "verifier")


class TestRefreshTokens:
    """Tests for token refresh."""

    @patch("flow.auth.httpx.Client")
    def test_refresh_tokens_success(self, mock_client_class):
        """Test successful token refresh."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        result = refresh_tokens("old-refresh")

        assert result.access_token == "refreshed-access"
        assert result.refresh_token == "new-refresh"

    @patch("flow.auth.httpx.Client")
    def test_refresh_tokens_keeps_old_refresh_token(self, mock_client_class):
        """Test that old refresh token is kept if not returned."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "refreshed-access",
            "expires_in": 3600,
            # No refresh_token in response
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response

        result = refresh_tokens("old-refresh")

        assert result.refresh_token == "old-refresh"


class TestGetAccessToken:
    """Tests for get_access_token function."""

    def test_get_access_token_not_authenticated(self, tmp_path, monkeypatch):
        """Test get_access_token when not authenticated."""
        auth_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)

        result = get_access_token()
        assert result is None

    def test_get_access_token_valid_token(self, tmp_path, monkeypatch):
        """Test get_access_token with valid (non-expired) token."""
        auth_file = tmp_path / "auth.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)
        monkeypatch.setattr("flow.auth.AUTH_DIR", tmp_path)

        # Save a token that expires in 1 hour
        token_data = TokenData(
            access_token="valid-token",
            refresh_token="refresh",
            expires_at=time.time() + 3600,
        )
        save_tokens(token_data)

        result = get_access_token()
        assert result == "valid-token"

    @patch("flow.auth.refresh_tokens")
    @patch("flow.auth.save_tokens")
    def test_get_access_token_refreshes_expired(self, mock_save, mock_refresh, tmp_path, monkeypatch):
        """Test get_access_token refreshes expired token."""
        auth_file = tmp_path / "auth.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)
        monkeypatch.setattr("flow.auth.AUTH_DIR", tmp_path)

        # Save a token that expires soon (within 5 minute buffer)
        token_data = TokenData(
            access_token="expired-token",
            refresh_token="refresh",
            expires_at=time.time() + 60,  # Expires in 1 minute
        )
        save_tokens(token_data)

        # Mock refresh to return new token
        new_token = TokenData(
            access_token="refreshed-token",
            refresh_token="new-refresh",
            expires_at=time.time() + 3600,
        )
        mock_refresh.return_value = new_token

        result = get_access_token()

        mock_refresh.assert_called_once_with("refresh")
        assert result == "refreshed-token"


class TestIsAuthenticated:
    """Tests for is_authenticated function."""

    def test_is_authenticated_true(self, tmp_path, monkeypatch):
        """Test is_authenticated returns True when authenticated."""
        auth_file = tmp_path / "auth.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)
        monkeypatch.setattr("flow.auth.AUTH_DIR", tmp_path)

        token_data = TokenData(
            access_token="token",
            refresh_token="refresh",
            expires_at=time.time() + 3600,
        )
        save_tokens(token_data)

        assert is_authenticated() is True

    def test_is_authenticated_false(self, tmp_path, monkeypatch):
        """Test is_authenticated returns False when not authenticated."""
        auth_file = tmp_path / "nonexistent.json"
        monkeypatch.setattr("flow.auth.AUTH_FILE", auth_file)

        assert is_authenticated() is False


class TestLogin:
    """Tests for login function."""

    @patch("flow.auth.webbrowser.open")
    def test_login_opens_browser(self, mock_open):
        """Test that login opens browser with correct URL."""
        verifier, state = login()

        mock_open.assert_called_once()
        url = mock_open.call_args[0][0]
        assert AUTHORIZATION_URL in url
        assert CLIENT_ID in url

    @patch("flow.auth.webbrowser.open")
    def test_login_returns_verifier_and_state(self, mock_open):
        """Test that login returns verifier and state."""
        verifier, state = login()

        assert isinstance(verifier, str)
        assert isinstance(state, str)
        assert len(verifier) > 0
        assert len(state) > 0


class TestCompleteLogin:
    """Tests for complete_login function."""

    @patch("flow.auth.exchange_code")
    @patch("flow.auth.save_tokens")
    def test_complete_login_success(self, mock_save, mock_exchange):
        """Test complete_login successfully exchanges code."""
        token_data = TokenData(
            access_token="access",
            refresh_token="refresh",
            expires_at=time.time() + 3600,
        )
        mock_exchange.return_value = token_data

        result = complete_login("auth-code", "verifier")

        mock_exchange.assert_called_once_with("auth-code", "verifier")
        mock_save.assert_called_once_with(token_data)
        assert result == token_data
