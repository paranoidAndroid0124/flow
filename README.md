# Flow

A vibe coding CLI tool with AI-powered code generation, review, scaffolding, and context management.

## Features

- **Code Generation**: Generate code from natural language prompts
- **Code Review**: Get AI feedback on your code with focus areas (security, performance, style, bugs)
- **Project Scaffolding**: Generate project structures for CLI apps, APIs, libraries, and web apps
- **Context Management**: Smart context collection from your codebase
- **Jira Integration**: Fetch issues, create tasks, and use issue context for AI generation
- **Multiple Providers**: Support for Anthropic Claude and local Ollama models

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd flow

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Configuration

Initialize the configuration file:

```bash
flow config init
```

Set your Anthropic API key:

```bash
flow config set anthropic.api_key YOUR_API_KEY
```

Or use an environment variable:

```bash
export ANTHROPIC_API_KEY=your-api-key
```

View current configuration:

```bash
flow config show
```

### Configuration Options

The config file is located at `~/.config/flow/config.toml`:

```toml
[default]
provider = "anthropic"  # or "ollama"
model = "claude-sonnet-4-20250514"

[anthropic]
api_key = "${ANTHROPIC_API_KEY}"

[ollama]
host = "http://localhost:11434"
model = "codellama"

[jira]
url = "${JIRA_URL}"
email = "${JIRA_EMAIL}"
api_token = "${JIRA_API_TOKEN}"
default_project = "PROJ"

[context]
max_files = 50
ignore = [".git", "node_modules", "__pycache__", ".venv"]
```

## Usage

### Generate Code

```bash
# Basic generation
flow generate "a function to parse CSV files"

# Specify language
flow generate "REST API endpoint for users" -l python

# Output to file
flow generate "a fibonacci function" -o fib.py

# Use specific file as context
flow generate "add error handling" -c src/utils.py

# Use Jira issue as context
flow generate "implement this feature" --jira PROJ-123
```

### Review Code

```bash
# Review a file
flow review src/utils.py

# Focus on specific area
flow review src/ --focus security
flow review src/api.py --focus performance

# Review staged git changes
flow review . --diff
```

Focus areas:
- `all` - Comprehensive review (default)
- `security` - Security vulnerabilities
- `performance` - Performance issues
- `style` - Code style and readability
- `bugs` - Potential bugs

### Scaffold Projects

```bash
# Create a CLI project
flow scaffold cli my-tool

# Create a REST API
flow scaffold api my-api

# Create a library
flow scaffold library my-lib

# Create a web app
flow scaffold webapp my-app

# Specify output directory
flow scaffold cli my-tool -o ~/projects
```

### Manage Context

```bash
# Show context info for current directory
flow context show

# Show detailed file list
flow context show -v

# Preview context that would be sent to AI
flow context preview

# Add pattern to ignore list
flow context ignore "*.log"
flow context ignore "build/"
```

### Jira Integration

Configure Jira credentials:

```bash
# Via environment variables (recommended)
export JIRA_URL=https://your-domain.atlassian.net
export JIRA_EMAIL=your@email.com
export JIRA_API_TOKEN=your-api-token

# Or via config
flow config set jira.url https://your-domain.atlassian.net
flow config set jira.email your@email.com
flow config set jira.api_token your-api-token
flow config set jira.default_project PROJ
```

Available commands:

```bash
# View an issue
flow jira view PROJ-123

# List your issues
flow jira mine

# List issues with filters
flow jira list --project PROJ
flow jira list --assignee me --status "In Progress"
flow jira list --jql "project = PROJ AND status = Open"

# Create an issue
flow jira create "Implement user auth" -p PROJ
flow jira create "Fix login bug" -t Bug -p PROJ --priority High

# Add a comment
flow jira comment PROJ-123 "Working on this now"

# Transition an issue
flow jira transition PROJ-123 "In Progress"
flow jira transition PROJ-123 Done

# List projects
flow jira projects

# Start working on an issue (with AI implementation plan)
flow jira work PROJ-123 --generate
```

## Using with Ollama

To use local models with Ollama:

1. Install Ollama: https://ollama.ai
2. Pull a model: `ollama pull codellama`
3. Configure Flow:

```bash
flow config set default.provider ollama
flow config set ollama.model codellama
```

## Development

Run tests:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=flow
```

## Project Structure

```
flow/
├── pyproject.toml
├── README.md
├── src/
│   └── flow/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── providers/
│       │   ├── base.py
│       │   ├── anthropic.py
│       │   └── ollama.py
│       ├── commands/
│       │   ├── generate.py
│       │   ├── review.py
│       │   ├── scaffold.py
│       │   ├── context.py
│       │   ├── config.py
│       │   └── jira.py
│       ├── integrations/
│       │   └── jira_client.py
│       ├── context/
│       │   ├── collector.py
│       │   └── indexer.py
│       └── utils/
│           └── files.py
└── tests/
```

## License

MIT
