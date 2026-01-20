"""Project scaffolding command."""

from pathlib import Path
from enum import Enum

import typer
from rich.console import Console
from rich.tree import Tree

console = Console()


class ProjectType(str, Enum):
    """Types of projects that can be scaffolded."""

    CLI = "cli"
    API = "api"
    LIBRARY = "library"
    WEBAPP = "webapp"


# Project templates
TEMPLATES: dict[ProjectType, dict[str, str | None]] = {
    ProjectType.CLI: {
        "src/{name}/__init__.py": '''"""{{name}} - A command-line tool."""

__version__ = "0.1.0"
''',
        "src/{name}/__main__.py": '''"""Entry point for {{name}}."""

from {{name}}.cli import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
''',
        "src/{name}/cli.py": '''"""CLI definitions using Typer."""

import typer
from rich.console import Console

from {{name}} import __version__

app = typer.Typer(
    name="{{name}}",
    help="{{name}} - A command-line tool.",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
) -> None:
    """{{name}} CLI."""
    if version:
        console.print(f"{{name}} version {__version__}")
        raise typer.Exit()


@app.command()
def hello(name: str = typer.Argument("World", help="Name to greet")) -> None:
    """Say hello."""
    console.print(f"Hello, {name}!")
''',
        "pyproject.toml": '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{name}}"
version = "0.1.0"
description = "A command-line tool"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "typer[all]>=0.9.0",
    "rich>=13.0.0",
]

[project.scripts]
{{name}} = "{{name}}.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["src/{{name}}"]
''',
        "README.md": '''# {{name}}

A command-line tool.

## Installation

```bash
pip install -e .
```

## Usage

```bash
{{name}} --help
{{name}} hello World
```
''',
        "tests/__init__.py": "",
        "tests/test_cli.py": '''"""Tests for CLI."""

from typer.testing import CliRunner
from {{name}}.cli import app


runner = CliRunner()


def test_hello():
    result = runner.invoke(app, ["hello", "Test"])
    assert result.exit_code == 0
    assert "Hello, Test!" in result.stdout
''',
        ".gitignore": '''__pycache__/
*.py[cod]
.venv/
dist/
*.egg-info/
.pytest_cache/
''',
    },
    ProjectType.API: {
        "src/{name}/__init__.py": '''"""{{name}} - A REST API."""

__version__ = "0.1.0"
''',
        "src/{name}/main.py": '''"""Main FastAPI application."""

from fastapi import FastAPI
from {{name}}.routes import router

app = FastAPI(
    title="{{name}}",
    version="0.1.0",
)

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
''',
        "src/{name}/routes.py": '''"""API routes."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/items")
def list_items():
    return {"items": []}


@router.get("/items/{item_id}")
def get_item(item_id: int):
    return {"id": item_id, "name": f"Item {item_id}"}
''',
        "pyproject.toml": '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{name}}"
version = "0.1.0"
description = "A REST API"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{{name}}"]
''',
        "README.md": '''# {{name}}

A REST API built with FastAPI.

## Installation

```bash
pip install -e ".[dev]"
```

## Running

```bash
uvicorn {{name}}.main:app --reload
```

## API Docs

Once running, visit:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)
''',
        "tests/__init__.py": "",
        "tests/test_api.py": '''"""Tests for API."""

from fastapi.testclient import TestClient
from {{name}}.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_items():
    response = client.get("/api/v1/items")
    assert response.status_code == 200
''',
        ".gitignore": '''__pycache__/
*.py[cod]
.venv/
dist/
*.egg-info/
.pytest_cache/
''',
    },
    ProjectType.LIBRARY: {
        "src/{name}/__init__.py": '''"""{{name}} - A Python library."""

__version__ = "0.1.0"

from {{name}}.core import example_function

__all__ = ["example_function"]
''',
        "src/{name}/core.py": '''"""Core functionality."""


def example_function(value: str) -> str:
    """An example function.

    Args:
        value: Input value.

    Returns:
        Processed value.
    """
    return f"processed: {value}"
''',
        "pyproject.toml": '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{name}}"
version = "0.1.0"
description = "A Python library"
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{{name}}"]
''',
        "README.md": '''# {{name}}

A Python library.

## Installation

```bash
pip install {{name}}
```

## Usage

```python
from {{name}} import example_function

result = example_function("hello")
print(result)  # "processed: hello"
```
''',
        "tests/__init__.py": "",
        "tests/test_core.py": '''"""Tests for core functionality."""

from {{name}} import example_function


def test_example_function():
    result = example_function("test")
    assert result == "processed: test"
''',
        ".gitignore": '''__pycache__/
*.py[cod]
.venv/
dist/
*.egg-info/
.pytest_cache/
''',
    },
    ProjectType.WEBAPP: {
        "src/{name}/__init__.py": '''"""{{name}} - A web application."""

__version__ = "0.1.0"
''',
        "src/{name}/app.py": '''"""Flask web application."""

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", title="{{name}}")


@app.route("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    app.run(debug=True)
''',
        "src/{name}/templates/index.html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <main>
        <h1>Welcome to {{ title }}</h1>
        <p>Your web application is running!</p>
    </main>
</body>
</html>
''',
        "src/{name}/static/style.css": '''* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: system-ui, -apple-system, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}

main {
    max-width: 800px;
    margin: 2rem auto;
    padding: 2rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
    margin-bottom: 1rem;
    color: #2563eb;
}
''',
        "pyproject.toml": '''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{{name}}"
version = "0.1.0"
description = "A web application"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "flask>=3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{{name}}"]
''',
        "README.md": '''# {{name}}

A web application built with Flask.

## Installation

```bash
pip install -e ".[dev]"
```

## Running

```bash
flask --app {{name}}.app run --debug
```

Then visit http://localhost:5000
''',
        "tests/__init__.py": "",
        ".gitignore": '''__pycache__/
*.py[cod]
.venv/
dist/
*.egg-info/
.pytest_cache/
instance/
''',
    },
}


def scaffold(
    project_type: ProjectType = typer.Argument(..., help="Type of project to scaffold"),
    name: str = typer.Argument(..., help="Project name"),
    output: Path = typer.Option(
        Path("."), "--output", "-o", help="Output directory"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing files"
    ),
) -> None:
    """Generate a new project structure.

    Examples:
        flow scaffold cli my-tool
        flow scaffold api my-api -o ~/projects
        flow scaffold library my-lib
    """
    # Normalize the project name (replace hyphens with underscores for Python)
    python_name = name.replace("-", "_")
    project_dir = output / name

    # Check if project already exists
    if project_dir.exists() and not force:
        console.print(f"[red]Directory already exists:[/red] {project_dir}")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    template = TEMPLATES.get(project_type)
    if not template:
        console.print(f"[red]Unknown project type:[/red] {project_type}")
        raise typer.Exit(1)

    # Create project structure
    created_files = []
    tree = Tree(f"[bold blue]{name}/[/bold blue]")

    for path_template, content in template.items():
        # Replace {name} in path
        rel_path = path_template.format(name=python_name)
        file_path = project_dir / rel_path

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Replace {{name}} in content
        if content:
            content = content.replace("{{name}}", python_name)
            file_path.write_text(content)
        else:
            file_path.touch()

        created_files.append(rel_path)
        _add_to_tree(tree, rel_path)

    console.print(f"\n[green]Created project:[/green] {project_dir}\n")
    console.print(tree)

    # Show next steps
    console.print(f"\n[bold]Next steps:[/bold]")
    console.print(f"  cd {name}")
    console.print(f"  python -m venv .venv && source .venv/bin/activate")
    console.print(f"  pip install -e \".[dev]\"")

    if project_type == ProjectType.CLI:
        console.print(f"  {python_name} --help")
    elif project_type == ProjectType.API:
        console.print(f"  uvicorn {python_name}.main:app --reload")
    elif project_type == ProjectType.WEBAPP:
        console.print(f"  flask --app {python_name}.app run --debug")


def _add_to_tree(tree: Tree, path: str) -> None:
    """Add a path to a Rich tree structure."""
    parts = path.split("/")
    current = tree
    for i, part in enumerate(parts):
        # Find or create child
        found = None
        for child in current.children:
            if child.label == part or child.label == f"[bold]{part}/[/bold]":
                found = child
                break

        if found:
            current = found
        else:
            is_dir = i < len(parts) - 1
            label = f"[bold]{part}/[/bold]" if is_dir else part
            current = current.add(label)
