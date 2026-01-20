"""OAuth authentication for Claude subscription."""

import base64
import hashlib
import json
import logging
import secrets
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# OAuth configuration (matches Claude Code)
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
AUTHORIZATION_URL = "https://console.anthropic.com/oauth/authorize"
TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
SCOPES = ["org:create_api_key", "user:profile", "user:inference"]

# Token storage
AUTH_DIR = Path.home() / ".config" / "flow"
AUTH_FILE = AUTH_DIR / "auth.json"


@dataclass
class TokenData:
    """OAuth token data."""

    access_token: str
    refresh_token: str
    expires_at: float


def generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256).

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate a random code_verifier (43-128 characters)
    code_verifier = secrets.token_urlsafe(32)

    # Create code_challenge using S256
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


def get_authorization_url(state: str, code_challenge: str) -> str:
    """Build the OAuth authorization URL with PKCE params.

    Args:
        state: Random state for CSRF protection
        code_challenge: PKCE code challenge

    Returns:
        Full authorization URL
    """
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(code: str, code_verifier: str) -> TokenData:
    """Exchange authorization code for tokens.

    Args:
        code: Authorization code from callback
        code_verifier: PKCE code verifier

    Returns:
        TokenData with access and refresh tokens

    Raises:
        Exception: If token exchange fails
    """
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }

    with httpx.Client() as client:
        response = client.post(TOKEN_URL, data=data)
        response.raise_for_status()
        token_data = response.json()

    expires_in = token_data.get("expires_in", 3600)
    expires_at = time.time() + expires_in

    return TokenData(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=expires_at,
    )


def refresh_tokens(refresh_token: str) -> TokenData:
    """Refresh expired access tokens.

    Args:
        refresh_token: The refresh token

    Returns:
        New TokenData with fresh tokens

    Raises:
        Exception: If refresh fails
    """
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    }

    with httpx.Client() as client:
        response = client.post(TOKEN_URL, data=data)
        response.raise_for_status()
        token_data = response.json()

    expires_in = token_data.get("expires_in", 3600)
    expires_at = time.time() + expires_in

    return TokenData(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token", refresh_token),
        expires_at=expires_at,
    )


def save_tokens(token_data: TokenData) -> None:
    """Save tokens to ~/.config/flow/auth.json.

    Args:
        token_data: Token data to save
    """
    AUTH_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "access_token": token_data.access_token,
        "refresh_token": token_data.refresh_token,
        "expires_at": token_data.expires_at,
    }

    with open(AUTH_FILE, "w") as f:
        json.dump(data, f, indent=2)

    # Set restrictive permissions (owner read/write only)
    AUTH_FILE.chmod(0o600)


def load_tokens() -> TokenData | None:
    """Load tokens from ~/.config/flow/auth.json.

    Returns:
        TokenData if tokens exist, None otherwise
    """
    if not AUTH_FILE.exists():
        return None

    try:
        with open(AUTH_FILE) as f:
            data = json.load(f)
        return TokenData(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data["expires_at"],
        )
    except (json.JSONDecodeError, KeyError):
        return None


def delete_tokens() -> bool:
    """Delete stored tokens.

    Returns:
        True if tokens were deleted, False if none existed
    """
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()
        return True
    return False


def get_access_token() -> str | None:
    """Get a valid access token, refreshing if needed.

    Returns:
        Valid access token or None if not authenticated
    """
    token_data = load_tokens()
    if token_data is None:
        return None

    # Check if token is expired (with 5 minute buffer)
    if time.time() >= token_data.expires_at - 300:
        try:
            token_data = refresh_tokens(token_data.refresh_token)
            save_tokens(token_data)
        except httpx.HTTPStatusError as e:
            logger.warning("Token refresh failed with HTTP error: %s", e.response.status_code)
            return None
        except httpx.RequestError as e:
            logger.warning("Token refresh failed with network error: %s", e)
            return None
        except Exception as e:
            logger.warning("Token refresh failed with unexpected error: %s", e)
            return None

    return token_data.access_token


def is_authenticated() -> bool:
    """Check if user is authenticated via OAuth.

    Returns:
        True if authenticated, False otherwise
    """
    return get_access_token() is not None


def login() -> tuple[str, str]:
    """Start OAuth login flow.

    Opens browser for authentication. User must copy the authorization
    code from the callback page and paste it into the CLI.

    Returns:
        Tuple of (code_verifier, state) for completing the login flow

    Raises:
        Exception: If authentication fails
    """
    # Generate PKCE values
    code_verifier, code_challenge = generate_pkce()

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(16)

    # Build authorization URL
    auth_url = get_authorization_url(state, code_challenge)

    # Open browser
    webbrowser.open(auth_url)

    # Return PKCE values for the code exchange step
    return code_verifier, state


def complete_login(code: str, code_verifier: str) -> TokenData:
    """Complete the OAuth login by exchanging the authorization code.

    Args:
        code: Authorization code from the callback page
        code_verifier: PKCE code verifier from login()

    Returns:
        TokenData on successful authentication

    Raises:
        Exception: If token exchange fails
    """
    # Exchange code for tokens
    token_data = exchange_code(code, code_verifier)

    # Save tokens
    save_tokens(token_data)

    return token_data
