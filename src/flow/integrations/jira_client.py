"""Jira integration client."""

import logging
from dataclasses import dataclass
from typing import Any

from jira import JIRA
from jira.exceptions import JIRAError

from flow.config import Config, JiraConfig

logger = logging.getLogger(__name__)


@dataclass
class JiraIssue:
    """Represents a Jira issue."""

    key: str
    summary: str
    description: str | None
    status: str
    issue_type: str
    priority: str | None
    assignee: str | None
    reporter: str | None
    labels: list[str]
    components: list[str]
    created: str
    updated: str
    url: str

    def to_context(self) -> str:
        """Format the issue as context for AI prompts."""
        parts = [
            f"# Jira Issue: {self.key}",
            f"**Summary:** {self.summary}",
            f"**Type:** {self.issue_type}",
            f"**Status:** {self.status}",
        ]

        if self.priority:
            parts.append(f"**Priority:** {self.priority}")
        if self.assignee:
            parts.append(f"**Assignee:** {self.assignee}")
        if self.labels:
            parts.append(f"**Labels:** {', '.join(self.labels)}")
        if self.components:
            parts.append(f"**Components:** {', '.join(self.components)}")
        if self.description:
            parts.append(f"\n## Description\n{self.description}")

        return "\n".join(parts)


class JiraClient:
    """Client for interacting with Jira."""

    def __init__(self, config: Config | None = None):
        """Initialize the Jira client.

        Args:
            config: Configuration object. If None, loads from default config.
        """
        self.config = config or Config.load()
        self._jira_config = self.config.jira
        self._client: JIRA | None = None

    @property
    def is_configured(self) -> bool:
        """Check if Jira is configured."""
        return self._jira_config.is_configured

    @property
    def client(self) -> JIRA:
        """Get or create the JIRA client."""
        if self._client is None:
            url = self._jira_config.url
            email = self._jira_config.email
            api_token = self._jira_config.api_token
            
            if not url or not email or not api_token:
                raise ValueError(
                    "Jira not configured. Set JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN "
                    "environment variables or run 'flow config set jira.<key> <value>'"
                )
            self._client = JIRA(
                server=url,
                basic_auth=(email, api_token),
            )
        return self._client

    @property
    def default_project(self) -> str | None:
        """Get the default project key."""
        return self._jira_config.default_project

    @property
    def base_url(self) -> str:
        """Get the Jira base URL.
        
        Returns:
            The Jira base URL.
            
        Raises:
            ValueError: If Jira URL is not configured.
        """
        if not self._jira_config.url:
            raise ValueError("Jira URL not configured")
        return self._jira_config.url

    def get_issue(self, issue_key: str) -> JiraIssue:
        """Get a Jira issue by key.

        Args:
            issue_key: The issue key (e.g., "PROJ-123")

        Returns:
            JiraIssue object
        """
        issue = self.client.issue(issue_key)
        return self._parse_issue(issue)

    def search_issues(
        self,
        jql: str | None = None,
        project: str | None = None,
        assignee: str | None = None,
        status: str | None = None,
        max_results: int = 50,
    ) -> list[JiraIssue]:
        """Search for Jira issues.

        Args:
            jql: Raw JQL query (if provided, other params are ignored)
            project: Project key to filter by
            assignee: Assignee to filter by (use "currentUser()" for self)
            status: Status to filter by
            max_results: Maximum number of results

        Returns:
            List of JiraIssue objects
        """
        if jql is None:
            # Build JQL from parameters
            conditions = []
            if project:
                conditions.append(f'project = "{project}"')
            elif self.default_project:
                conditions.append(f'project = "{self.default_project}"')
            if assignee:
                conditions.append(f"assignee = {assignee}")
            if status:
                conditions.append(f'status = "{status}"')

            jql = " AND ".join(conditions) if conditions else "ORDER BY updated DESC"

        issues = self.client.search_issues(jql, maxResults=max_results)
        return [self._parse_issue(issue) for issue in issues]

    def get_my_issues(self, max_results: int = 20) -> list[JiraIssue]:
        """Get issues assigned to the current user.

        Args:
            max_results: Maximum number of results

        Returns:
            List of JiraIssue objects
        """
        jql = "assignee = currentUser() AND resolution = Unresolved ORDER BY updated DESC"
        return self.search_issues(jql=jql, max_results=max_results)

    def create_issue(
        self,
        summary: str,
        description: str | None = None,
        issue_type: str = "Task",
        project: str | None = None,
        labels: list[str] | None = None,
        priority: str | None = None,
    ) -> JiraIssue:
        """Create a new Jira issue.

        Args:
            summary: Issue summary
            description: Issue description
            issue_type: Type of issue (Task, Bug, Story, etc.)
            project: Project key (uses default if not specified)
            labels: Labels to add
            priority: Priority name

        Returns:
            Created JiraIssue object
        """
        project_key = project or self.default_project
        if not project_key:
            raise ValueError("No project specified and no default project configured")

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }

        if description:
            fields["description"] = description
        if labels:
            fields["labels"] = labels
        if priority:
            fields["priority"] = {"name": priority}

        issue = self.client.create_issue(fields=fields)
        return self._parse_issue(issue)

    def add_comment(self, issue_key: str, comment: str) -> None:
        """Add a comment to an issue.

        Args:
            issue_key: The issue key
            comment: Comment text
        """
        self.client.add_comment(issue_key, comment)

    def transition_issue(self, issue_key: str, status: str) -> None:
        """Transition an issue to a new status.

        Args:
            issue_key: The issue key
            status: Target status name
        """
        transitions = self.client.transitions(issue_key)
        transition_id = None

        for t in transitions:
            if t["name"].lower() == status.lower():
                transition_id = t["id"]
                break

        if transition_id is None:
            available = [t["name"] for t in transitions]
            raise ValueError(
                f"Invalid status '{status}'. Available transitions: {', '.join(available)}"
            )

        self.client.transition_issue(issue_key, transition_id)

    def get_projects(self) -> list[dict[str, str]]:
        """Get all accessible projects.

        Returns:
            List of project info dicts with 'key' and 'name'
        """
        projects = self.client.projects()
        return [{"key": p.key, "name": p.name} for p in projects]

    def _parse_issue(self, issue: Any) -> JiraIssue:
        """Parse a JIRA issue into our dataclass.

        Args:
            issue: Raw JIRA issue object

        Returns:
            JiraIssue object
        """
        fields = issue.fields

        return JiraIssue(
            key=issue.key,
            summary=fields.summary,
            description=fields.description,
            status=fields.status.name,
            issue_type=fields.issuetype.name,
            priority=fields.priority.name if fields.priority else None,
            assignee=fields.assignee.displayName if fields.assignee else None,
            reporter=fields.reporter.displayName if fields.reporter else None,
            labels=list(fields.labels) if fields.labels else [],
            components=[c.name for c in fields.components] if fields.components else [],
            created=str(fields.created),
            updated=str(fields.updated),
            url=f"{self.base_url}/browse/{issue.key}",
        )
