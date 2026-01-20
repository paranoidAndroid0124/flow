"""Authentication management commands."""

import json
from pathlib import Path

import typer
from rich.console import Console

from flow import auth
from flow.config import get_config

app = typer.Typer(help="Authentication management")
console = Console()

# Claude Code credentials location
CLAUDE_CODE_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"


@app.command()
def login() -> None:
    """Login with your Claude subscription (Pro/Max) via OAuth."""
    if auth.is_authenticated():
        console.print("[yellow]Already authenticated via OAuth.[/yellow]")
        console.print("Run [bold]flow auth logout[/bold] first to re-authenticate.")
        raise typer.Exit(1)

    console.print("Opening browser for authentication...")
    console.print("[dim]Please log in with your Claude account and authorize the app.[/dim]\n")

    try:
        code_verifier, state = auth.login()
    except Exception as e:
        console.print(f"[red]Failed to open browser:[/red] {e}")
        raise typer.Exit(1)

    console.print("[green]Browser opened![/green]")
    console.print("\nAfter authorizing, you'll be redirected to a page with an authorization code.")
    console.print("Copy the code and paste it below.\n")

    # Prompt user for the authorization code
    code = typer.prompt("Authorization code")

    if not code or not code.strip():
        console.print("[red]No authorization code provided.[/red]")
        raise typer.Exit(1)

    try:
        auth.complete_login(code.strip(), code_verifier)
        console.print("\n[green]Successfully authenticated![/green]")
    except Exception as e:
        console.print(f"\n[red]Authentication failed:[/red] {e}")
        console.print("\n[dim]Make sure you copied the complete authorization code.[/dim]")
        raise typer.Exit(1)


@app.command()
def logout() -> None:
    """Logout and delete stored OAuth tokens."""
    if auth.delete_tokens():
        console.print("[green]Successfully logged out.[/green]")
    else:
        console.print("[yellow]No OAuth tokens found.[/yellow]")


@app.command("import")
def import_tokens() -> None:
    """Import OAuth tokens from Claude Code.

    If you have Claude Code authenticated, this imports those tokens
    so Flow can use your Claude subscription.
    """
    if not CLAUDE_CODE_CREDENTIALS.exists():
        console.print("[red]Claude Code credentials not found.[/red]")
        console.print(f"\nExpected location: {CLAUDE_CODE_CREDENTIALS}")
        console.print("\nMake sure Claude Code is installed and authenticated:")
        console.print("  1. Install Claude Code: npm install -g @anthropic-ai/claude-code")
        console.print("  2. Run: claude")
        console.print("  3. Complete the login flow")
        console.print("  4. Then run: flow auth import")
        raise typer.Exit(1)

    try:
        with open(CLAUDE_CODE_CREDENTIALS) as f:
            creds = json.load(f)

        # Claude Code stores tokens under claudeAiOauth key
        oauth_creds = creds.get("claudeAiOauth", creds)

        access_token = oauth_creds.get("accessToken") or oauth_creds.get("access_token")
        refresh_token = oauth_creds.get("refreshToken") or oauth_creds.get("refresh_token")
        expires_at = oauth_creds.get("expiresAt") or oauth_creds.get("expires_at")

        if not access_token or not refresh_token:
            console.print("[red]Invalid Claude Code credentials format.[/red]")
            console.print(f"[dim]Keys found: {list(creds.keys())}[/dim]")
            raise typer.Exit(1)

        # Convert expiresAt from milliseconds to seconds if needed
        if expires_at and expires_at > 1e12:
            expires_at = expires_at / 1000

        token_data = auth.TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at or 0,
        )
        auth.save_tokens(token_data)

        console.print("[green]Successfully imported tokens from Claude Code![/green]")
        console.print("\nYou can now use Flow with your Claude subscription.")

    except json.JSONDecodeError:
        console.print("[red]Failed to parse Claude Code credentials.[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error importing tokens:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show current authentication status."""
    config = get_config()

    # Check OAuth first
    if auth.is_authenticated():
        console.print("[green]Authenticated via OAuth (Claude subscription)[/green]")
        token_data = auth.load_tokens()
        if token_data:
            import time

            remaining = token_data.expires_at - time.time()
            if remaining > 0:
                minutes = int(remaining // 60)
                console.print(f"[dim]Token expires in {minutes} minutes[/dim]")
        return

    # Check API key
    api_key = config.anthropic.api_key
    if api_key:
        masked_key = f"...{api_key[-4:]}"
        console.print(f"[green]Authenticated via API key ({masked_key})[/green]")
        return

    # Not authenticated
    console.print("[yellow]Not authenticated[/yellow]")
    console.print("\nTo authenticate, either:")
    console.print("  1. Run [bold]flow auth login[/bold] (uses your Claude Pro/Max subscription)")
    console.print("  2. Set [bold]ANTHROPIC_API_KEY[/bold] environment variable")
    console.print("  3. Run [bold]flow config set anthropic.api_key YOUR_KEY[/bold]")
