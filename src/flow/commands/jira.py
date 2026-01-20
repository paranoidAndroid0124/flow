"""Jira integration commands."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from flow.config import get_config
from flow.integrations.jira_client import JiraClient
from flow.providers import get_provider

app = typer.Typer(help="Jira integration commands")
console = Console()


def _get_jira_client() -> JiraClient:
    """Get a configured Jira client or exit with error."""
    client = JiraClient()
    if not client.is_configured:
        console.print("[red]Jira not configured.[/red]")
        console.print("\nSet these environment variables:")
        console.print("  JIRA_URL - Your Jira instance URL")
        console.print("  JIRA_EMAIL - Your Jira email")
        console.print("  JIRA_API_TOKEN - Your Jira API token")
        console.print("\nOr configure via:")
        console.print("  flow config set jira.url https://your-domain.atlassian.net")
        console.print("  flow config set jira.email your@email.com")
        console.print("  flow config set jira.api_token your-api-token")
        raise typer.Exit(1)
    return client


@app.command("view")
def view_issue(
    issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
) -> None:
    """View details of a Jira issue.

    Examples:
        flow jira view PROJ-123
    """
    client = _get_jira_client()

    try:
        with console.status(f"[bold blue]Fetching {issue_key}...[/bold blue]"):
            issue = client.get_issue(issue_key)

        # Display issue details
        content = f"""**Type:** {issue.issue_type}  |  **Status:** {issue.status}  |  **Priority:** {issue.priority or 'None'}

**Assignee:** {issue.assignee or 'Unassigned'}  |  **Reporter:** {issue.reporter or 'Unknown'}

**Labels:** {', '.join(issue.labels) if issue.labels else 'None'}
**Components:** {', '.join(issue.components) if issue.components else 'None'}

---

{issue.description or '_No description_'}

---
**URL:** {issue.url}
"""
        console.print(Panel(
            Markdown(content),
            title=f"[bold]{issue.key}[/bold]: {issue.summary}",
            border_style="blue",
        ))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def list_issues(
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Project key to filter by"
    ),
    assignee: Optional[str] = typer.Option(
        None, "--assignee", "-a", help="Assignee (use 'me' for yourself)"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Status to filter by"
    ),
    jql: Optional[str] = typer.Option(
        None, "--jql", help="Raw JQL query"
    ),
    limit: int = typer.Option(
        20, "--limit", "-n", help="Maximum number of results"
    ),
) -> None:
    """List Jira issues.

    Examples:
        flow jira list --project PROJ
        flow jira list --assignee me
        flow jira list --jql "project = PROJ AND status = 'In Progress'"
    """
    client = _get_jira_client()

    # Convert 'me' to currentUser()
    if assignee == "me":
        assignee = "currentUser()"

    try:
        with console.status("[bold blue]Searching issues...[/bold blue]"):
            issues = client.search_issues(
                jql=jql,
                project=project,
                assignee=assignee,
                status=status,
                max_results=limit,
            )

        if not issues:
            console.print("[yellow]No issues found.[/yellow]")
            return

        table = Table(title=f"Jira Issues ({len(issues)} results)")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Type", style="dim")
        table.add_column("Status", style="green")
        table.add_column("Summary")
        table.add_column("Assignee", style="dim")

        for issue in issues:
            summary = issue.summary[:50] + "..." if len(issue.summary) > 50 else issue.summary
            table.add_row(
                issue.key,
                issue.issue_type,
                issue.status,
                summary,
                issue.assignee or "-",
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("mine")
def my_issues(
    limit: int = typer.Option(
        20, "--limit", "-n", help="Maximum number of results"
    ),
) -> None:
    """List issues assigned to you.

    Examples:
        flow jira mine
        flow jira mine -n 10
    """
    client = _get_jira_client()

    try:
        with console.status("[bold blue]Fetching your issues...[/bold blue]"):
            issues = client.get_my_issues(max_results=limit)

        if not issues:
            console.print("[green]No open issues assigned to you.[/green]")
            return

        table = Table(title="My Issues")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Type", style="dim")
        table.add_column("Status", style="green")
        table.add_column("Priority", style="yellow")
        table.add_column("Summary")

        for issue in issues:
            summary = issue.summary[:50] + "..." if len(issue.summary) > 50 else issue.summary
            table.add_row(
                issue.key,
                issue.issue_type,
                issue.status,
                issue.priority or "-",
                summary,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("create")
def create_issue(
    summary: str = typer.Argument(..., help="Issue summary"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Issue description"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Project key"
    ),
    issue_type: str = typer.Option(
        "Task", "--type", "-t", help="Issue type (Task, Bug, Story, etc.)"
    ),
    labels: Optional[str] = typer.Option(
        None, "--labels", "-l", help="Comma-separated labels"
    ),
    priority: Optional[str] = typer.Option(
        None, "--priority", help="Priority (Highest, High, Medium, Low, Lowest)"
    ),
) -> None:
    """Create a new Jira issue.

    Examples:
        flow jira create "Implement user auth" -p PROJ
        flow jira create "Fix login bug" -t Bug -p PROJ --priority High
    """
    client = _get_jira_client()

    label_list = [l.strip() for l in labels.split(",")] if labels else None

    try:
        with console.status("[bold blue]Creating issue...[/bold blue]"):
            issue = client.create_issue(
                summary=summary,
                description=description,
                issue_type=issue_type,
                project=project,
                labels=label_list,
                priority=priority,
            )

        console.print(f"[green]Created issue:[/green] {issue.key}")
        console.print(f"[dim]URL: {issue.url}[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("comment")
def add_comment(
    issue_key: str = typer.Argument(..., help="Issue key"),
    comment: str = typer.Argument(..., help="Comment text"),
) -> None:
    """Add a comment to a Jira issue.

    Examples:
        flow jira comment PROJ-123 "Working on this now"
    """
    client = _get_jira_client()

    try:
        with console.status(f"[bold blue]Adding comment to {issue_key}...[/bold blue]"):
            client.add_comment(issue_key, comment)

        console.print(f"[green]Comment added to {issue_key}[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("transition")
def transition_issue(
    issue_key: str = typer.Argument(..., help="Issue key"),
    status: str = typer.Argument(..., help="Target status"),
) -> None:
    """Transition an issue to a new status.

    Examples:
        flow jira transition PROJ-123 "In Progress"
        flow jira transition PROJ-123 Done
    """
    client = _get_jira_client()

    try:
        with console.status(f"[bold blue]Transitioning {issue_key}...[/bold blue]"):
            client.transition_issue(issue_key, status)

        console.print(f"[green]{issue_key} transitioned to '{status}'[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("projects")
def list_projects() -> None:
    """List all accessible Jira projects.

    Examples:
        flow jira projects
    """
    client = _get_jira_client()

    try:
        with console.status("[bold blue]Fetching projects...[/bold blue]"):
            projects = client.get_projects()

        if not projects:
            console.print("[yellow]No projects found.[/yellow]")
            return

        table = Table(title="Jira Projects")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Name")

        for project in projects:
            table.add_row(project["key"], project["name"])

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("work")
def work_on_issue(
    issue_key: str = typer.Argument(..., help="Issue key to work on"),
    generate: bool = typer.Option(
        False, "--generate", "-g", help="Generate implementation plan using AI"
    ),
) -> None:
    """Start working on a Jira issue.

    Fetches issue details, optionally generates an implementation plan,
    and can transition the issue to 'In Progress'.

    Examples:
        flow jira work PROJ-123
        flow jira work PROJ-123 --generate
    """
    client = _get_jira_client()

    try:
        with console.status(f"[bold blue]Fetching {issue_key}...[/bold blue]"):
            issue = client.get_issue(issue_key)

        # Display issue
        console.print(Panel(
            f"**{issue.summary}**\n\n{issue.description or '_No description_'}",
            title=f"{issue.key} ({issue.status})",
            border_style="blue",
        ))

        if generate:
            console.print()
            with console.status("[bold blue]Generating implementation plan...[/bold blue]"):
                provider = get_provider()
                result = provider.generate(
                    prompt=f"""Based on this Jira issue, create a brief implementation plan:

{issue.to_context()}

Provide:
1. A brief analysis of what needs to be done
2. Key technical considerations
3. A step-by-step implementation plan
4. Potential edge cases to consider

Keep it concise and actionable.""",
                    system="You are a senior software engineer helping plan implementation of features and bug fixes.",
                )

            console.print(Panel(
                Markdown(result.content),
                title="Implementation Plan",
                border_style="green",
            ))

        # Ask if they want to transition
        if issue.status.lower() not in ["in progress", "in development"]:
            console.print()
            if typer.confirm(f"Transition {issue_key} to 'In Progress'?"):
                try:
                    client.transition_issue(issue_key, "In Progress")
                    console.print(f"[green]{issue_key} is now 'In Progress'[/green]")
                except ValueError as e:
                    console.print(f"[yellow]Could not transition: {e}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
