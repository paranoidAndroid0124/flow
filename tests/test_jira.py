"""Tests for Jira integration module."""

from unittest.mock import Mock, patch, MagicMock

import pytest

from flow.integrations.jira_client import JiraClient, JiraIssue
from flow.config import Config, JiraConfig


class TestJiraIssue:
    """Tests for JiraIssue dataclass."""

    def test_jira_issue_creation(self):
        """Test JiraIssue creation."""
        issue = JiraIssue(
            key="TEST-123",
            summary="Test issue",
            description="Test description",
            status="Open",
            issue_type="Bug",
            priority="High",
            assignee="john.doe",
            reporter="jane.doe",
            labels=["bug", "urgent"],
            components=["backend"],
            created="2024-01-01T00:00:00",
            updated="2024-01-02T00:00:00",
            url="https://jira.example.com/browse/TEST-123",
        )

        assert issue.key == "TEST-123"
        assert issue.summary == "Test issue"
        assert issue.status == "Open"
        assert issue.labels == ["bug", "urgent"]

    def test_to_context(self):
        """Test JiraIssue.to_context() method."""
        issue = JiraIssue(
            key="TEST-123",
            summary="Implement feature X",
            description="Detailed description here",
            status="In Progress",
            issue_type="Story",
            priority="Medium",
            assignee="developer",
            reporter="pm",
            labels=["feature"],
            components=["frontend"],
            created="2024-01-01T00:00:00",
            updated="2024-01-02T00:00:00",
            url="https://jira.example.com/browse/TEST-123",
        )

        context = issue.to_context()

        assert "TEST-123" in context
        assert "Implement feature X" in context
        assert "Story" in context
        assert "In Progress" in context
        assert "Medium" in context
        assert "developer" in context
        assert "feature" in context
        assert "frontend" in context
        assert "Detailed description here" in context

    def test_to_context_without_optional_fields(self):
        """Test to_context with missing optional fields."""
        issue = JiraIssue(
            key="TEST-456",
            summary="Minimal issue",
            description=None,
            status="Open",
            issue_type="Task",
            priority=None,
            assignee=None,
            reporter=None,
            labels=[],
            components=[],
            created="2024-01-01T00:00:00",
            updated="2024-01-01T00:00:00",
            url="https://jira.example.com/browse/TEST-456",
        )

        context = issue.to_context()

        assert "TEST-456" in context
        assert "Minimal issue" in context
        # Should not crash with None values


class TestJiraClient:
    """Tests for JiraClient class."""

    def test_is_configured_false(self):
        """Test is_configured returns False when not configured."""
        config = Config()
        config.jira = JiraConfig()  # Empty config

        client = JiraClient(config)
        assert client.is_configured is False

    def test_is_configured_true(self):
        """Test is_configured returns True when configured."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token123",
        )

        client = JiraClient(config)
        assert client.is_configured is True

    def test_is_configured_partial(self):
        """Test is_configured returns False with partial config."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token=None,  # Missing token
        )

        client = JiraClient(config)
        assert client.is_configured is False

    def test_client_raises_without_config(self):
        """Test accessing client raises error when not configured."""
        config = Config()
        config.jira = JiraConfig()

        client = JiraClient(config)

        with pytest.raises(ValueError, match="Jira not configured"):
            _ = client.client

    def test_default_project(self):
        """Test default_project property."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
            default_project="PROJ",
        )

        client = JiraClient(config)
        assert client.default_project == "PROJ"

    def test_base_url(self):
        """Test base_url property."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        client = JiraClient(config)
        assert client.base_url == "https://jira.example.com"

    def test_base_url_raises_without_url(self):
        """Test base_url raises when URL not configured."""
        config = Config()
        config.jira = JiraConfig()

        client = JiraClient(config)

        with pytest.raises(ValueError, match="Jira URL not configured"):
            _ = client.base_url

    @patch("flow.integrations.jira_client.JIRA")
    def test_get_issue(self, mock_jira_class):
        """Test get_issue method."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        # Mock JIRA client
        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        # Mock issue response - use spec_set to properly mock .name attribute
        mock_status = Mock()
        mock_status.name = "Open"
        mock_issuetype = Mock()
        mock_issuetype.name = "Bug"
        mock_priority = Mock()
        mock_priority.name = "High"
        mock_assignee = Mock()
        mock_assignee.displayName = "John"
        mock_reporter = Mock()
        mock_reporter.displayName = "Jane"
        mock_component = Mock()
        mock_component.name = "comp1"

        mock_issue = Mock()
        mock_issue.key = "TEST-123"
        mock_issue.fields = Mock(
            summary="Test issue",
            description="Description",
            status=mock_status,
            issuetype=mock_issuetype,
            priority=mock_priority,
            assignee=mock_assignee,
            reporter=mock_reporter,
            labels=["label1"],
            components=[mock_component],
            created="2024-01-01",
            updated="2024-01-02",
        )
        mock_jira.issue.return_value = mock_issue

        client = JiraClient(config)
        result = client.get_issue("TEST-123")

        assert result.key == "TEST-123"
        assert result.summary == "Test issue"
        assert result.status == "Open"
        mock_jira.issue.assert_called_once_with("TEST-123")

    @patch("flow.integrations.jira_client.JIRA")
    def test_search_issues_with_jql(self, mock_jira_class):
        """Test search_issues with JQL query."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        mock_issue = Mock()
        mock_issue.key = "TEST-1"
        mock_issue.fields = Mock(
            summary="Issue 1",
            description=None,
            status=Mock(name="Open"),
            issuetype=Mock(name="Task"),
            priority=None,
            assignee=None,
            reporter=None,
            labels=[],
            components=[],
            created="2024-01-01",
            updated="2024-01-01",
        )
        mock_jira.search_issues.return_value = [mock_issue]

        client = JiraClient(config)
        results = client.search_issues(jql="project = TEST")

        assert len(results) == 1
        assert results[0].key == "TEST-1"
        mock_jira.search_issues.assert_called_once_with(
            "project = TEST", maxResults=50
        )

    @patch("flow.integrations.jira_client.JIRA")
    def test_search_issues_builds_jql(self, mock_jira_class):
        """Test search_issues builds JQL from parameters."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira
        mock_jira.search_issues.return_value = []

        client = JiraClient(config)
        client.search_issues(
            project="PROJ",
            assignee="currentUser()",
            status="In Progress",
            max_results=10,
        )

        call_args = mock_jira.search_issues.call_args
        jql = call_args[0][0]
        assert 'project = "PROJ"' in jql
        assert "assignee = currentUser()" in jql
        assert 'status = "In Progress"' in jql

    @patch("flow.integrations.jira_client.JIRA")
    def test_get_my_issues(self, mock_jira_class):
        """Test get_my_issues method."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira
        mock_jira.search_issues.return_value = []

        client = JiraClient(config)
        client.get_my_issues(max_results=10)

        call_args = mock_jira.search_issues.call_args
        jql = call_args[0][0]
        assert "assignee = currentUser()" in jql
        assert "resolution = Unresolved" in jql

    @patch("flow.integrations.jira_client.JIRA")
    def test_create_issue(self, mock_jira_class):
        """Test create_issue method."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
            default_project="PROJ",
        )

        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        mock_issue = Mock()
        mock_issue.key = "PROJ-999"
        mock_issue.fields = Mock(
            summary="New issue",
            description="Description",
            status=Mock(name="Open"),
            issuetype=Mock(name="Task"),
            priority=None,
            assignee=None,
            reporter=None,
            labels=[],
            components=[],
            created="2024-01-01",
            updated="2024-01-01",
        )
        mock_jira.create_issue.return_value = mock_issue

        client = JiraClient(config)
        result = client.create_issue(
            summary="New issue",
            description="Description",
            issue_type="Task",
        )

        assert result.key == "PROJ-999"
        mock_jira.create_issue.assert_called_once()

    @patch("flow.integrations.jira_client.JIRA")
    def test_create_issue_without_project_raises(self, mock_jira_class):
        """Test create_issue raises without project."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
            default_project=None,
        )

        client = JiraClient(config)

        with pytest.raises(ValueError, match="No project specified"):
            client.create_issue(summary="Test")

    @patch("flow.integrations.jira_client.JIRA")
    def test_add_comment(self, mock_jira_class):
        """Test add_comment method."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        client = JiraClient(config)
        client.add_comment("TEST-123", "My comment")

        mock_jira.add_comment.assert_called_once_with("TEST-123", "My comment")

    @patch("flow.integrations.jira_client.JIRA")
    def test_transition_issue(self, mock_jira_class):
        """Test transition_issue method."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira
        mock_jira.transitions.return_value = [
            {"id": "11", "name": "In Progress"},
            {"id": "21", "name": "Done"},
        ]

        client = JiraClient(config)
        client.transition_issue("TEST-123", "Done")

        mock_jira.transition_issue.assert_called_once_with("TEST-123", "21")

    @patch("flow.integrations.jira_client.JIRA")
    def test_transition_issue_invalid_status(self, mock_jira_class):
        """Test transition_issue raises for invalid status."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira
        mock_jira.transitions.return_value = [
            {"id": "11", "name": "In Progress"},
        ]

        client = JiraClient(config)

        with pytest.raises(ValueError, match="Invalid status"):
            client.transition_issue("TEST-123", "Invalid Status")

    @patch("flow.integrations.jira_client.JIRA")
    def test_get_projects(self, mock_jira_class):
        """Test get_projects method."""
        config = Config()
        config.jira = JiraConfig(
            url="https://jira.example.com",
            email="test@example.com",
            api_token="token",
        )

        mock_jira = Mock()
        mock_jira_class.return_value = mock_jira

        # Create proper mock objects with explicit attribute assignment
        mock_project1 = Mock()
        mock_project1.key = "PROJ1"
        mock_project1.name = "Project One"
        mock_project2 = Mock()
        mock_project2.key = "PROJ2"
        mock_project2.name = "Project Two"
        mock_jira.projects.return_value = [mock_project1, mock_project2]

        client = JiraClient(config)
        result = client.get_projects()

        assert len(result) == 2
        assert result[0] == {"key": "PROJ1", "name": "Project One"}
        assert result[1] == {"key": "PROJ2", "name": "Project Two"}
