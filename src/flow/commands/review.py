"""Code review command."""

import subprocess
from pathlib import Path
from enum import Enum

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from flow.providers import get_provider
from flow.context.collector import ContextCollector

console = Console()


class ReviewFocus(str, Enum):
    """Focus areas for code review."""

    ALL = "all"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    BUGS = "bugs"


REVIEW_SYSTEM_PROMPTS = {
    ReviewFocus.ALL: """You are an expert code reviewer. Review the provided code comprehensively, looking at:
- Code quality and readability
- Potential bugs or errors
- Security issues
- Performance concerns
- Best practices and patterns

Provide constructive feedback with specific suggestions for improvement. Use markdown formatting.""",

    ReviewFocus.SECURITY: """You are a security-focused code reviewer. Analyze the provided code for:
- Injection vulnerabilities (SQL, command, XSS)
- Authentication/authorization issues
- Data exposure risks
- Insecure dependencies
- Input validation problems
- Cryptography misuse

Provide specific security concerns with remediation suggestions.""",

    ReviewFocus.PERFORMANCE: """You are a performance-focused code reviewer. Analyze the provided code for:
- Algorithmic complexity issues
- Memory inefficiencies
- Unnecessary computations
- Database query optimization
- Caching opportunities
- Resource management

Provide specific performance concerns with optimization suggestions.""",

    ReviewFocus.STYLE: """You are a code style reviewer. Analyze the provided code for:
- Naming conventions
- Code organization
- Documentation quality
- Consistency with common patterns
- Readability improvements
- Refactoring opportunities

Provide specific style suggestions to improve code quality.""",

    ReviewFocus.BUGS: """You are a bug-finding code reviewer. Analyze the provided code for:
- Logic errors
- Edge cases not handled
- Null/undefined issues
- Type mismatches
- Race conditions
- Error handling gaps

Provide specific bug risks with suggested fixes.""",
}


def review(
    path: Path = typer.Argument(
        ..., help="File or directory to review", exists=True
    ),
    focus: ReviewFocus = typer.Option(
        ReviewFocus.ALL, "--focus", "-f", help="Focus area for review"
    ),
    diff: bool = typer.Option(
        False, "--diff", "-d", help="Review staged git changes only"
    ),
) -> None:
    """Get AI feedback on code.

    Examples:
        flow review src/utils.py
        flow review src/ --focus security
        flow review . --diff
    """
    # Get the code to review
    if diff:
        code = _get_staged_diff()
        if not code:
            console.print("[yellow]No staged changes to review.[/yellow]")
            console.print("Stage changes with: git add <files>")
            raise typer.Exit(1)
        source_description = "staged changes"
    else:
        collector = ContextCollector()
        code = collector.collect_from_path(path)
        if not code:
            console.print(f"[yellow]No reviewable code found at {path}[/yellow]")
            raise typer.Exit(1)
        source_description = str(path)

    # Build the prompt
    prompt = f"Please review the following code:\n\n{code}"

    try:
        with console.status(f"[bold blue]Reviewing {source_description}...[/bold blue]"):
            provider = get_provider()
            result = provider.generate(
                prompt=prompt,
                system=REVIEW_SYSTEM_PROMPTS[focus],
            )

        # Display the result
        console.print()
        title = f"Code Review ({focus.value})"
        console.print(Panel(Markdown(result.content), title=title, border_style="blue"))

        # Show usage stats
        if result.usage:
            tokens = result.usage.get("input_tokens", 0) + result.usage.get("output_tokens", 0)
            console.print(f"\n[dim]Model: {result.model} | Tokens: {tokens}[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _get_staged_diff() -> str | None:
    """Get the staged git diff.

    Returns:
        Diff content or None if no staged changes
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            check=True,
        )
        diff = result.stdout.strip()
        return diff if diff else None
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        console.print("[yellow]Git not found. Cannot review staged changes.[/yellow]")
        return None
