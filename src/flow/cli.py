"""Main CLI definitions using Typer."""

import typer
from rich.console import Console

from flow import __version__
from flow.commands import generate, review, scaffold, context, config, jira

app = typer.Typer(
    name="flow",
    help="A vibe coding CLI tool with AI-powered code generation, review, and scaffolding.",
)

console = Console()

# Register command groups
app.add_typer(context.app, name="context", help="Manage codebase context")
app.add_typer(config.app, name="config", help="Manage configuration")
app.add_typer(jira.app, name="jira", help="Jira integration")

# Register standalone commands
app.command(name="generate")(generate.generate)
app.command(name="review")(review.review)
app.command(name="scaffold")(scaffold.scaffold)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit"
    ),
) -> None:
    """Flow - AI-powered vibe coding assistant."""
    if version:
        console.print(f"flow version {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()
