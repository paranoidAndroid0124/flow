"""Code generation command."""

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from flow.providers import get_provider
from flow.context.collector import ContextCollector

console = Console()


GENERATE_SYSTEM_PROMPT = """You are an expert programmer assistant. Generate clean, well-documented code based on the user's request.

Guidelines:
- Write idiomatic, production-quality code
- Include type hints (for Python) or appropriate type annotations
- Add brief comments for complex logic
- Follow best practices for the language
- If generating a complete file, include necessary imports

If context is provided, use it to understand the existing codebase style and patterns.

Respond with just the code unless the user asks for explanations. Use markdown code blocks with the appropriate language tag."""


def generate(
    prompt: str = typer.Argument(..., help="What code to generate"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write output to file"
    ),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Target programming language"
    ),
    context: Path | None = typer.Option(
        None, "--context", "-c", help="File or directory to use as context"
    ),
    jira_issue: str | None = typer.Option(
        None, "--jira", "-j", help="Jira issue key to use as context"
    ),
    no_context: bool = typer.Option(
        False, "--no-context", help="Disable automatic context collection"
    ),
) -> None:
    """Generate code from a natural language prompt.

    Examples:
        flow generate "a function to parse CSV files"
        flow generate "REST API endpoint for users" -l python -o api.py
        flow generate "add error handling" -c src/utils.py
        flow generate "implement this feature" --jira PROJ-123
    """
    # Build the prompt
    full_prompt = prompt
    if language:
        full_prompt = f"Generate {language} code: {prompt}"

    # Collect context if specified or auto-detect
    context_parts = []

    # Add Jira context if specified
    if jira_issue:
        try:
            from flow.integrations.jira_client import JiraClient
            jira_client = JiraClient()
            if jira_client.is_configured:
                with console.status(f"[bold blue]Fetching {jira_issue}...[/bold blue]"):
                    issue = jira_client.get_issue(jira_issue)
                context_parts.append(issue.to_context())
                console.print(f"[dim]Using Jira context: {jira_issue}[/dim]")
            else:
                console.print(f"[yellow]Jira not configured, skipping issue context[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Could not fetch Jira issue: {e}[/yellow]")

    # Add file context
    if context:
        collector = ContextCollector()
        file_context = collector.collect_from_path(context)
        if file_context:
            context_parts.append(file_context)
        console.print(f"[dim]Using context from: {context}[/dim]")
    elif not no_context:
        # Try to collect some context from current directory
        collector = ContextCollector()
        project_context = collector.collect_summary()
        if project_context:
            context_parts.append(project_context)
            console.print("[dim]Using project context[/dim]")

    context_content = "\n\n".join(context_parts) if context_parts else None

    try:
        with console.status("[bold blue]Generating code...[/bold blue]"):
            provider = get_provider()
            result = provider.generate(
                prompt=full_prompt,
                system=GENERATE_SYSTEM_PROMPT,
                context=context_content,
            )

        # Display the result
        console.print()
        console.print(Panel(Markdown(result.content), title="Generated Code", border_style="green"))

        # Show usage stats
        if result.usage:
            tokens = result.usage.get("input_tokens", 0) + result.usage.get("output_tokens", 0)
            console.print(f"\n[dim]Model: {result.model} | Tokens: {tokens}[/dim]")

        # Write to file if requested
        if output:
            # Extract just the code from markdown if present
            code = _extract_code(result.content)
            output.write_text(code)
            console.print(f"\n[green]Written to {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _extract_code(content: str) -> str:
    """Extract code from markdown code blocks."""
    lines = content.split("\n")
    code_lines = []
    in_code_block = False

    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            code_lines.append(line)

    # If no code blocks found, return original content
    if not code_lines:
        return content

    return "\n".join(code_lines)
