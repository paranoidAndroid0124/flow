"""Configuration management commands."""

import typer
from rich.console import Console
from rich.table import Table

from flow.config import (
    init_config,
    get_config,
    set_config_value,
    CONFIG_FILE,
)

app = typer.Typer(help="Manage Flow configuration")
console = Console()


@app.command()
def init() -> None:
    """Initialize Flow configuration file."""
    config_path = init_config()
    console.print(f"[green]Configuration initialized at:[/green] {config_path}")
    console.print("\n[yellow]Remember to set your API key:[/yellow]")
    console.print("  flow config set anthropic.api_key YOUR_API_KEY")
    console.print("\n[dim]Or set the ANTHROPIC_API_KEY environment variable[/dim]")


@app.command()
def show() -> None:
    """Show current configuration."""
    if not CONFIG_FILE.exists():
        console.print("[yellow]No configuration file found.[/yellow]")
        console.print("Run [bold]flow config init[/bold] to create one.")
        raise typer.Exit(1)

    config = get_config()

    table = Table(title="Flow Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Provider", config.provider)
    table.add_row("Model", config.model)
    table.add_row("Config File", str(CONFIG_FILE))

    # Show provider-specific settings
    if config.provider == "anthropic":
        api_key = config.anthropic.api_key
        masked_key = f"...{api_key[-4:]}" if api_key else "[red]Not set[/red]"
        table.add_row("API Key", masked_key)
    elif config.provider == "ollama":
        table.add_row("Ollama Host", config.ollama.host or "")
        table.add_row("Ollama Model", config.ollama.model or "")

    table.add_row("Context Max Files", str(config.context.max_files))
    table.add_row("Context Ignore", ", ".join(config.context.ignore))

    console.print(table)


@app.command("set")
def set_value(
    key: str = typer.Argument(..., help="Config key (e.g., 'default.provider')"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    try:
        set_config_value(key, value)
        console.print(f"[green]Set {key} = {value}[/green]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def path() -> None:
    """Show configuration file path."""
    console.print(str(CONFIG_FILE))
