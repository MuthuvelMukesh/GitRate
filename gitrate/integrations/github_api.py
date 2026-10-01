"""GitHub API wrapper for comprehensive repository data fetching."""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

from github import Github
from github.GithubException import GithubException, RateLimitExceededException

from gitrate.core.models import (
    RepositoryInfo, CommitInfo, ContributorInfo, 
    DependencyInfo, TestingInfo, DocumentationInfo, RepositoryData
)
from gitrate.utils.constants import DEPENDENCY_FILES, CI_CD_FILES
from gitrate.utils.config import settings
from gitrate.utils.helpers import parse_github_url, sanitize_string

logger = logging.getLogger(__name__)


class GitHubFetcher:
    """GitHub API client for repository data collection."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client.
        
        Args:
            token: GitHub API token (uses settings if not provided)
        """
        self.token = token or settings.github_token
        self.base_url = settings.github_api_base_url
        
        # Initialize GitHub client (with or without authentication)
        if self.token:
            self.client = Github(self.token)
            logger.info("Initialized authenticated GitHub client")
        else:
            self.client = Github()
            logger.warning("Using anonymous GitHub API (rate limited)")
        
        self.rate_limited = False
        self.rate_limit_reset: Optional[datetime] = None
    
    async def fetch_repository_data(
        self,
        owner: str,
        repo: str,
    ) -> Tuple[Optional[RepositoryData], Optional[str]]:
        """
        Fetch comprehensive repository data.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Tuple of (RepositoryData, error_message)
        """
        try:
            logger.info(f"Starting data fetch for {owner}/{repo}")
            
            # Check rate limiting
            if self.rate_limited:
                if datetime.utcnow() < self.rate_limit_reset:
                    error = f"Rate limited until {self.rate_limit_reset}"
                    logger.warning(error)
                    return None, error
                else:
                    self.rate_limited = False
            
            # Get repository object
            try:
                gh_repo = self.client.get_user(owner).get_repo(repo)
            except RateLimitExceededException as e:
                self.rate_limited = True
                self.rate_limit_reset = datetime.utcnow() + timedelta(hours=1)
                return None, f"GitHub API rate limited: {str(e)}"
            except GithubException as e:
                return None, f"GitHub API error: {str(e)}"
            
            # Collect data in parallel
            repo_info = self._extract_repo_info(gh_repo)
            commits = await self._fetch_commit_info(owner, repo)
            contributors = await self._fetch_contributor_info(gh_repo)
            dependencies = await self._fetch_dependency_info(owner, repo)
            testing = await self._fetch_testing_info(owner, repo)
            documentation = await self._fetch_documentation_info(gh_repo)
            
            # Compile results
            repo_data = RepositoryData(
                repo_info=repo_info,
                commits=commits,
                contributors=contributors,
                dependencies=dependencies,
                testing=testing,
                documentation=documentation,
                raw_data={}  # Can add raw GitHub data if needed
            )
            
            logger.info(f"Successfully fetched data for {owner}/{repo}")
            return repo_data, None
            
        except Exception as e:
            error = f"Unexpected error fetching repository data: {str(e)}"
            logger.error(error, exc_info=True)
            return None, error
    
    def _extract_repo_info(self, gh_repo) -> RepositoryInfo:
        """Extract basic repository information."""
        try:
            # Get languages
            languages = gh_repo.get_languages() or {}
            
            # Determine primary language
            primary_language = None
            if languages:
                primary_language = max(languages, key=languages.get)
            
            repo_info = RepositoryInfo(
                owner=gh_repo.owner.login,
                name=gh_repo.name,
                full_name=gh_repo.full_name,
                url=gh_repo.html_url,
                description=sanitize_string(gh_repo.description or ""),
                homepage=gh_repo.homepage,
                
                stars=gh_repo.stargazers_count,
                forks=gh_repo.forks_count,
                watchers=gh_repo.watchers_count,
                open_issues=gh_repo.open_issues_count,
                
                language=primary_language,
                languages=languages,
                
                license=gh_repo.license.name if gh_repo.license else None,
                is_private=gh_repo.private,
                is_fork=gh_repo.fork,
                
                created_at=gh_repo.created_at,
                updated_at=gh_repo.updated_at,
                pushed_at=gh_repo.pushed_at,
                
                size_kb=gh_repo.size,
            )
            
            logger.debug(f"Extracted repo info: {repo_info.full_name}")
            return repo_info
            
        except Exception as e:
            logger.error(f"Error extracting repo info: {str(e)}", exc_info=True)
            raise
    
    async def _fetch_commit_info(
        self,
        owner: str,
        repo: str,
    ) -> CommitInfo:
        """Fetch commit statistics."""
        try:
            gh_repo = self.client.get_user(owner).get_repo(repo)
            
            # Get all commits (may be paginated)
            commits = list(gh_repo.get_commits())
            total_commits = len(commits) if commits else 0
            
            # Calculate commits in time windows
            now = datetime.utcnow()
            thirty_days_ago = now - timedelta(days=30)
            ninety_days_ago = now - timedelta(days=90)
            
            commits_30days = 0
            commits_90days = 0
            last_commit_date = None
            first_commit_date = None
            
            if commits:
                last_commit_date = commits[0].commit.author.date
                first_commit_date = commits[-1].commit.author.date if len(commits) > 0 else None
                
                for commit in commits:
                    commit_date = commit.commit.author.date
                    if commit_date >= thirty_days_ago:
                        commits_30days += 1
                    if commit_date >= ninety_days_ago:
                        commits_90days += 1
            
            # Determine commit frequency
            commit_frequency = self._determine_commit_frequency(commits_30days)
            
            commit_info = CommitInfo(
                total_commits=total_commits,
                commits_30days=commits_30days,
                commits_90days=commits_90days,
                last_commit_date=last_commit_date,
                first_commit_date=first_commit_date,
                commit_frequency=commit_frequency,
            )
            
            logger.debug(f"Fetched commit info: {total_commits} total")
            return commit_info
            
        except Exception as e:
            logger.warning(f"Error fetching commit info: {str(e)}")
            return CommitInfo()
    
    async def _fetch_contributor_info(self, gh_repo) -> ContributorInfo:
        """Fetch contributor statistics."""
        try:
            contributors = list(gh_repo.get_contributors())
            
            if not contributors:
                return ContributorInfo()
            
            total_contributors = len(contributors)
            top_contributors = []
            
            # Get top 5 contributors
            for i, contributor in enumerate(contributors[:5]):
                top_contributors.append({
                    "login": contributor.login,
                    "contributions": contributor.contributions,
                    "rank": i + 1,
                })
            
            # Calculate concentration (% by top contributor)
            total_contributions = sum(c.contributions for c in contributors)
            top_contributor_concentration = 0.0
            if total_contributions > 0 and contributors:
                top_contributor_concentration = (contributors[0].contributions / total_contributions) * 100
            
            # Calculate churn rate (contributors from last 90 days vs all)
            now = datetime.utcnow()
            ninety_days_ago = now - timedelta(days=90)
            
            active_30days = 0  # Simplified - would need commit analysis
            for contributor in contributors:
                if contributor.updated_at and contributor.updated_at >= ninety_days_ago:
                    active_30days += 1
            
            churn_rate = 0.0
            if total_contributors > 0:
                churn_rate = (total_contributors - active_30days) / total_contributors
            
            contributor_info = ContributorInfo(
                total_contributors=total_contributors,
                top_contributors=top_contributors,
                contributor_concentration=top_contributor_concentration,
                active_contributors_30days=active_30days,
                churn_rate=churn_rate,
            )
            
            logger.debug(f"Fetched contributor info: {total_contributors} contributors")
            return contributor_info
            
        except Exception as e:
            logger.warning(f"Error fetching contributor info: {str(e)}")
            return ContributorInfo()
    
    async def _fetch_dependency_info(self, owner: str, repo: str) -> DependencyInfo:
        """Fetch dependency information."""
        try:
            gh_repo = self.client.get_user(owner).get_repo(repo)
            
            dependency_info = DependencyInfo()
            
            # Check for dependency files
            for file_type, file_names in DEPENDENCY_FILES.items():
                for file_name in file_names:
                    try:
                        contents = gh_repo.get_contents(file_name)
                        dependency_info.has_requirements = True
                        dependency_info.dependency_file_type = file_type
                        
                        # Parse dependencies (simplified)
                        raw_content = contents.decoded_content.decode()
                        dep_count = len([line for line in raw_content.split('\n') 
                                       if line.strip() and not line.startswith('#')])
                        dependency_info.total_dependencies = dep_count
                        
                        logger.debug(f"Found {file_type} dependencies: {dep_count}")
                        return dependency_info
                        
                    except:
                        continue
            
            logger.debug("No dependency files found")
            return dependency_info
            
        except Exception as e:
            logger.warning(f"Error fetching dependency info: {str(e)}")
            return DependencyInfo()
    
    async def _fetch_testing_info(self, owner: str, repo: str) -> TestingInfo:
        """Fetch testing and CI/CD information."""
        try:
            gh_repo = self.client.get_user(owner).get_repo(repo)
            
            testing_info = TestingInfo()
            
            # Check for test directories
            test_dirs = ["tests", "test", "spec", "specs", "__tests__"]
            for test_dir in test_dirs:
                try:
                    gh_repo.get_contents(test_dir)
                    testing_info.has_tests = True
                    testing_info.test_framework = self._detect_test_framework(test_dir)
                    logger.debug(f"Found test directory: {test_dir}")
                    break
                except:
                    continue
            
            # Check for CI/CD configuration
            for ci_type, ci_path in CI_CD_FILES.items():
                try:
                    gh_repo.get_contents(ci_path)
                    testing_info.has_ci_cd = True
                    testing_info.ci_cd_type = ci_type
                    logger.debug(f"Found CI/CD: {ci_type}")
                    break
                except:
                    continue
            
            return testing_info
            
        except Exception as e:
            logger.warning(f"Error fetching testing info: {str(e)}")
            return TestingInfo()
    
    async def _fetch_documentation_info(self, gh_repo) -> DocumentationInfo:
        """Fetch documentation information."""
        try:
            doc_info = DocumentationInfo()
            
            # Check README
            try:
                readme = gh_repo.get_readme()
                doc_info.has_readme = True
                decoded_content = readme.decoded_content.decode()
                doc_info.readme_length = len(decoded_content)
                doc_info.readme_snippet = decoded_content[:500]
            except:
                pass
            
            # Check other docs
            for doc_file in ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "ARCHITECTURE.md"]:
                try:
                    gh_repo.get_contents(doc_file)
                    if "CONTRIBUTING" in doc_file:
                        doc_info.has_contributing = True
                    elif "CODE_OF_CONDUCT" in doc_file:
                        doc_info.has_code_of_conduct = True
                    elif "ARCHITECTURE" in doc_file:
                        doc_info.has_architecture_docs = True
                except:
                    pass
            
            # Calculate documentation score
            doc_score = 0
            if doc_info.has_readme:
                doc_score += 40
            if doc_info.has_contributing:
                doc_score += 30
            if doc_info.has_code_of_conduct:
                doc_score += 15
            if doc_info.has_architecture_docs:
                doc_score += 15
            
            doc_info.documentation_quality_score = float(doc_score)
            
            logger.debug(f"Documentation score: {doc_score}")
            return doc_info
            
        except Exception as e:
            logger.warning(f"Error fetching documentation info: {str(e)}")
            return DocumentationInfo()
    
    @staticmethod
    def _determine_commit_frequency(commits_30days: int) -> str:
        """Determine commit frequency based on 30-day commit count."""
        if commits_30days == 0:
            return "stale"
        elif commits_30days < 5:
            return "monthly"
        elif commits_30days < 25:
            return "weekly"
        elif commits_30days < 100:
            return "daily"
        else:
            return "multiple_daily"
    
    @staticmethod
    def _detect_test_framework(test_dir: str) -> Optional[str]:
        """Detect test framework from directory name."""
        framework_map = {
            "test": "unittest",
            "tests": "pytest",
            "spec": "rspec",
            "specs": "rspec",
            "__tests__": "jest",
        }
        return framework_map.get(test_dir.lower())


async def fetch_repo_data_async(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> Tuple[Optional[RepositoryData], Optional[str]]:
    """
    Convenience async function to fetch repository data.
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub API token
        
    Returns:
        Tuple of (RepositoryData, error_message)
    """
    fetcher = GitHubFetcher(token)
    return await fetcher.fetch_repository_data(owner, repo)
