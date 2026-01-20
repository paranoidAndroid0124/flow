"""Context management commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from flow.config import get_config, set_config_value, CONFIG_FILE
from flow.context.collector import ContextCollector
from flow.context.indexer import FileIndexer

app = typer.Typer(help="Manage codebase context")
console = Console()


@app.command()
def show(
    path: Path = typer.Argument(
        Path("."), help="Directory to analyze"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed file list"
    ),
) -> None:
    """Show current context information.

    Displays what files Flow would include when gathering context.
    """
    path = path.resolve()

    if not path.exists():
        console.print(f"[red]Path does not exist:[/red] {path}")
        raise typer.Exit(1)

    with console.status("[bold blue]Analyzing project...[/bold blue]"):
        indexer = FileIndexer(path)
        indexer.build_index()

    files = indexer.get_all_files()
    summary = indexer.get_summary()
    config = get_config()

    # Show summary table
    table = Table(title=f"Context: {path.name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total files", str(len(files)))
    table.add_row("Max files (config)", str(config.context.max_files))
    table.add_row("Ignore patterns", ", ".join(config.context.ignore))

    console.print(table)
    console.print()

    # Show file type breakdown
    if summary:
        type_table = Table(title="File Types")
        type_table.add_column("Extension", style="cyan")
        type_table.add_column("Count", style="green", justify="right")

        for ext, count in list(summary.items())[:15]:
            type_table.add_row(ext, str(count))

        console.print(type_table)

    # Show file list if verbose
    if verbose and files:
        console.print()
        tree = Tree(f"[bold]{path.name}/[/bold]")
        _build_file_tree(tree, files[:50], path)
        console.print(tree)

        if len(files) > 50:
            console.print(f"\n[dim]... and {len(files) - 50} more files[/dim]")


@app.command()
def add(
    pattern: str = typer.Argument(..., help="Pattern to add to context"),
) -> None:
    """Add a file pattern to include in context.

    Note: This is a placeholder for future functionality.
    Currently, Flow includes all text files not in ignore patterns.
    """
    console.print(f"[yellow]Pattern-based inclusion not yet implemented.[/yellow]")
    console.print(f"Flow currently includes all text files except those matching ignore patterns.")
    console.print(f"\nTo modify ignore patterns, edit: {CONFIG_FILE}")


@app.command()
def ignore(
    pattern: str = typer.Argument(..., help="Pattern to ignore"),
) -> None:
    """Add a pattern to the ignore list.

    Patterns use gitignore-style matching.

    Examples:
        flow context ignore "*.log"
        flow context ignore "build/"
        flow context ignore "test_*.py"
    """
    config = get_config()
    current_ignore = list(config.context.ignore)

    if pattern in current_ignore:
        console.print(f"[yellow]Pattern already in ignore list:[/yellow] {pattern}")
        return

    current_ignore.append(pattern)

    # We need to manually update the config file for this
    # since it's a list value
    if not CONFIG_FILE.exists():
        from flow.config import init_config
        init_config()

    import sys
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    import tomli_w

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    if "context" not in data:
        data["context"] = {}
    data["context"]["ignore"] = current_ignore

    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)

    console.print(f"[green]Added to ignore list:[/green] {pattern}")


@app.command()
def preview(
    path: Path = typer.Argument(
        Path("."), help="Directory to preview context from"
    ),
    limit: int = typer.Option(
        5, "--limit", "-n", help="Number of files to preview"
    ),
) -> None:
    """Preview what context would be sent to the AI.

    Shows a sample of the context that would be collected.
    """
    path = path.resolve()

    if not path.exists():
        console.print(f"[red]Path does not exist:[/red] {path}")
        raise typer.Exit(1)

    collector = ContextCollector()

    if path.is_file():
        content = collector.collect_from_path(path)
    else:
        # Get limited context for preview
        indexer = FileIndexer(path)
        indexer.build_index()
        files = indexer.get_all_files()[:limit]

        parts = []
        for info in files:
            file_content = collector._format_file(info.path)
            if file_content:
                parts.append(file_content)

        content = "\n\n".join(parts)

    if not content:
        console.print("[yellow]No context content available.[/yellow]")
        return

    # Truncate for display
    max_chars = 5000
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n... (truncated, {len(content)} total chars)"

    console.print("[bold]Context Preview:[/bold]")
    console.print()
    console.print(content)


def _build_file_tree(tree: Tree, files: list, root: Path) -> None:
    """Build a file tree for display.

    Args:
        tree: Rich Tree to add to
        files: List of FileInfo objects
        root: Root path
    """
    # Build a nested dict structure first
    structure: dict = {}
    for f in files:
        parts = f.relative_path.split("/")
        current = structure
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current[part] = None  # File
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]

    # Recursively add to tree
    _add_dict_to_tree(tree, structure)


def _add_dict_to_tree(tree: Tree, structure: dict) -> None:
    """Recursively add dictionary structure to tree."""
    for name, children in sorted(structure.items()):
        if children is None:
            tree.add(name)
        else:
            subtree = tree.add(f"[bold]{name}/[/bold]")
            _add_dict_to_tree(subtree, children)
