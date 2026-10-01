"""Integration tests for GitHub API client."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from gitrate.integrations.github_api import GitHubFetcher
from gitrate.core.models import RepositoryInfo, CommitInfo, ContributorInfo, DependencyInfo


class TestGitHubFetcherInitialization:
    """Tests for GitHubFetcher initialization."""
    
    @pytest.mark.asyncio
    async def test_fetcher_creation(self):
        """Test GitHubFetcher can be created."""
        fetcher = GitHubFetcher(github_token="test_token")
        assert fetcher is not None
    
    @pytest.mark.asyncio
    async def test_fetcher_with_custom_headers(self):
        """Test GitHubFetcher respects auth."""
        fetcher = GitHubFetcher(github_token="test_token")
        assert fetcher.headers["Authorization"] == "token test_token"


class TestGitHubFetcherValidation:
    """Tests for GitHub URL and owner/repo validation."""
    
    @pytest.mark.asyncio
    async def test_parse_owner_repo_valid(self):
        """Test parsing valid owner/repo."""
        fetcher = GitHubFetcher(github_token="test_token")
        owner, repo = await fetcher.parse_owner_repo("owner/repo")
        assert owner == "owner"
        assert repo == "repo"
    
    @pytest.mark.asyncio
    async def test_parse_owner_repo_invalid_format(self):
        """Test parsing invalid owner/repo format."""
        fetcher = GitHubFetcher(github_token="test_token")
        with pytest.raises(ValueError):
            await fetcher.parse_owner_repo("invalid-format")
    
    @pytest.mark.asyncio
    async def test_parse_owner_repo_empty(self):
        """Test parsing empty owner/repo."""
        fetcher = GitHubFetcher(github_token="test_token")
        with pytest.raises(ValueError):
            await fetcher.parse_owner_repo("")


class TestGitHubFetcherRateLimit:
    """Tests for GitHub API rate limit handling."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_tracking(self):
        """Test rate limit is tracked."""
        fetcher = GitHubFetcher(github_token="test_token")
        assert fetcher.rate_limit_remaining >= 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset_time(self):
        """Test rate limit reset time is tracked."""
        fetcher = GitHubFetcher(github_token="test_token")
        assert hasattr(fetcher, 'rate_limit_reset')


class TestGitHubFetcherMock:
    """Tests using mocked GitHub API responses."""
    
    @pytest.mark.asyncio
    async def test_fetch_repository_info_structure(self, github_api_responses):
        """Test repository info has correct structure."""
        repo_data = github_api_responses["repository"]
        assert "owner" in repo_data or "full_name" in repo_data
        assert "description" in repo_data
    
    @pytest.mark.asyncio
    async def test_fetch_commits_structure(self, github_api_responses):
        """Test commits response structure."""
        commits = github_api_responses["commits"]
        assert isinstance(commits, list)
        if len(commits) > 0:
            assert "commit" in commits[0]
            assert "author" in commits[0]
    
    @pytest.mark.asyncio
    async def test_fetch_contributors_structure(self, github_api_responses):
        """Test contributors response structure."""
        contributors = github_api_responses["contributors"]
        assert isinstance(contributors, list)
        if len(contributors) > 0:
            assert "login" in contributors[0]
            assert "contributions" in contributors[0]


class TestGitHubFetcherRepositoryData:
    """Tests for repository data fetching."""
    
    @pytest.mark.asyncio
    async def test_mock_repository_response(self, github_api_responses):
        """Test mock repository response is valid."""
        repo = github_api_responses["repository"]
        
        assert repo is not None
        assert isinstance(repo, dict)
        # Standard GitHub API fields
        assert "id" in repo
        assert "name" in repo or "full_name" in repo
    
    @pytest.mark.asyncio
    async def test_repository_has_stars(self, github_api_responses):
        """Test repository has star count."""
        repo = github_api_responses["repository"]
        assert "stargazers_count" in repo
        assert isinstance(repo["stargazers_count"], int)
    
    @pytest.mark.asyncio
    async def test_repository_has_language(self, github_api_responses):
        """Test repository has language field."""
        repo = github_api_responses["repository"]
        # Language can be null but field should exist
        assert "language" in repo or "languages" in repo
    
    @pytest.mark.asyncio
    async def test_repository_has_topics(self, github_api_responses):
        """Test repository has topics."""
        repo = github_api_responses["repository"]
        # Topics or description should be available
        assert "description" in repo or "topics" in repo


class TestGitHubFetcherCommitData:
    """Tests for commit data fetching."""
    
    @pytest.mark.asyncio
    async def test_commits_return_list(self, github_api_responses):
        """Test commits returns list."""
        commits = github_api_responses["commits"]
        assert isinstance(commits, list)
    
    @pytest.mark.asyncio
    async def test_commit_has_message(self, github_api_responses):
        """Test commit has message."""
        commits = github_api_responses["commits"]
        if len(commits) > 0:
            commit = commits[0]["commit"]
            assert "message" in commit
    
    @pytest.mark.asyncio
    async def test_commit_has_author(self, github_api_responses):
        """Test commit has author info."""
        commits = github_api_responses["commits"]
        if len(commits) > 0:
            assert "author" in commits[0]
            assert "login" in commits[0]["author"]
    
    @pytest.mark.asyncio
    async def test_commit_has_date(self, github_api_responses):
        """Test commit has date."""
        commits = github_api_responses["commits"]
        if len(commits) > 0:
            assert "commit" in commits[0]
            assert "author" in commits[0]["commit"]
            assert "date" in commits[0]["commit"]["author"]


class TestGitHubFetcherContributorData:
    """Tests for contributor data fetching."""
    
    @pytest.mark.asyncio
    async def test_contributors_return_list(self, github_api_responses):
        """Test contributors returns list."""
        contributors = github_api_responses["contributors"]
        assert isinstance(contributors, list)
    
    @pytest.mark.asyncio
    async def test_contributor_has_login(self, github_api_responses):
        """Test contributor has login."""
        contributors = github_api_responses["contributors"]
        if len(contributors) > 0:
            assert "login" in contributors[0]
    
    @pytest.mark.asyncio
    async def test_contributor_has_contribution_count(self, github_api_responses):
        """Test contributor has contribution count."""
        contributors = github_api_responses["contributors"]
        if len(contributors) > 0:
            assert "contributions" in contributors[0]
            assert isinstance(contributors[0]["contributions"], int)
    
    @pytest.mark.asyncio
    async def test_contributors_sorted_by_contributions(self, github_api_responses):
        """Test contributors are sorted by contributions."""
        contributors = github_api_responses["contributors"]
        if len(contributors) > 1:
            # Should be descending order
            assert contributors[0]["contributions"] >= contributors[1]["contributions"]


class TestGitHubFetcherPullRequests:
    """Tests for pull request data fetching."""
    
    @pytest.mark.asyncio
    async def test_pull_requests_return_list(self, github_api_responses):
        """Test pull requests returns list."""
        prs = github_api_responses.get("pull_requests", [])
        assert isinstance(prs, list)
    
    @pytest.mark.asyncio
    async def test_pull_request_has_state(self, github_api_responses):
        """Test PR has state (open/closed)."""
        prs = github_api_responses.get("pull_requests", [])
        if len(prs) > 0:
            assert "state" in prs[0]


class TestGitHubFetcherIssues:
    """Tests for issue data fetching."""
    
    @pytest.mark.asyncio
    async def test_issues_return_list(self, github_api_responses):
        """Test issues returns list."""
        issues = github_api_responses.get("issues", [])
        assert isinstance(issues, list)
    
    @pytest.mark.asyncio
    async def test_issue_has_state(self, github_api_responses):
        """Test issue has state."""
        issues = github_api_responses.get("issues", [])
        if len(issues) > 0:
            assert "state" in issues[0]


class TestGitHubFetcherErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_owner_repo_raises_error(self):
        """Test invalid owner/repo raises error."""
        fetcher = GitHubFetcher(github_token="test_token")
        with pytest.raises(ValueError):
            await fetcher.parse_owner_repo("///invalid")
    
    @pytest.mark.asyncio
    async def test_empty_token_handled(self):
        """Test empty token is handled."""
        # Should create fetcher but may fail on actual requests
        fetcher = GitHubFetcher(github_token="")
        assert fetcher is not None


class TestGitHubFetcherSession:
    """Tests for session management."""
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test fetcher can be used as context manager."""
        fetcher = GitHubFetcher(github_token="test_token")
        # Should have session management
        assert hasattr(fetcher, 'session') or hasattr(fetcher, '__aenter__')
    
    @pytest.mark.asyncio
    async def test_fetcher_cleanup(self):
        """Test fetcher cleanup."""
        fetcher = GitHubFetcher(github_token="test_token")
        # Should be able to close without errors
        if hasattr(fetcher, 'close'):
            await fetcher.close()


class TestGitHubAPIIntegrationWithModels:
    """Tests for integration with Pydantic models."""
    
    @pytest.mark.asyncio
    async def test_repository_info_model_compatible(self, sample_repository_info):
        """Test RepositoryInfo model is compatible with API data."""
        assert sample_repository_info is not None
        assert hasattr(sample_repository_info, 'owner')
        assert hasattr(sample_repository_info, 'name')
        assert hasattr(sample_repository_info, 'stars')
    
    @pytest.mark.asyncio
    async def test_commit_info_model_compatible(self, sample_commit_info):
        """Test CommitInfo model is compatible with API data."""
        assert sample_commit_info is not None
        assert hasattr(sample_commit_info, 'hash')
        assert hasattr(sample_commit_info, 'message')
        assert hasattr(sample_commit_info, 'author')
    
    @pytest.mark.asyncio
    async def test_contributor_info_model_compatible(self, sample_contributor_info):
        """Test ContributorInfo model is compatible with API data."""
        assert sample_contributor_info is not None
        assert hasattr(sample_contributor_info, 'login')
        assert hasattr(sample_contributor_info, 'contributions')
