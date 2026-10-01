"""Pytest configuration and fixtures for testing."""

import os
import pytest
import asyncio
from datetime import datetime
from typing import AsyncGenerator

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from gitrate.database.models import Base, Repository, Audit, AuditFinding
from gitrate.core.cache import RedisCache
from gitrate.core.models import (
    RepositoryInfo, CommitInfo, ContributorInfo, DependencyInfo,
    TestingInfo, DocumentationInfo, RepositoryData, AuditScores,
    AuditFinding as AuditFindingModel
)
from gitrate.utils.config import Settings


# ===== PYTEST CONFIGURATION =====

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Mark test as unit test")
    config.addinivalue_line("markers", "integration: Mark test as integration test")
    config.addinivalue_line("markers", "slow: Mark test as slow")
    config.addinivalue_line("markers", "async: Mark test as async")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ===== DATABASE FIXTURES =====

@pytest.fixture
async def test_db_engine():
    """Create test database engine."""
    # Use SQLite for testing (in-memory)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


# ===== CACHE FIXTURES =====

@pytest.fixture
async def mock_redis_cache():
    """Create mock Redis cache (no actual Redis needed)."""
    cache = RedisCache(redis_url="redis://localhost:6379/0")
    
    # Mock the client with in-memory dict
    cache.cache_data = {}
    cache.connected = True
    
    # Override methods to use dict
    async def mock_set(key: str, value, ttl_seconds: int = 86400) -> bool:
        import json
        cache.cache_data[key] = {
            "value": json.dumps(value, default=str),
            "ttl": ttl_seconds,
        }
        return True
    
    async def mock_get(key: str):
        import json
        if key in cache.cache_data:
            return json.loads(cache.cache_data[key]["value"])
        return None
    
    async def mock_delete(key: str) -> bool:
        if key in cache.cache_data:
            del cache.cache_data[key]
            return True
        return False
    
    cache.set = mock_set
    cache.get = mock_get
    cache.delete = mock_delete
    
    return cache


# ===== MODEL FIXTURES =====

@pytest.fixture
def sample_repository_info():
    """Create sample RepositoryInfo."""
    return RepositoryInfo(
        owner="pytorch",
        repo="pytorch",
        url="https://github.com/pytorch/pytorch",
        description="Tensors and Dynamic neural networks",
        language="C++",
        license="BSD-3-Clause",
        stars=65000,
        forks=18000,
        open_issues=5000,
        created_at=datetime(2016, 1, 14),
        updated_at=datetime(2025, 2, 4),
    )


@pytest.fixture
def sample_commit_info():
    """Create sample CommitInfo."""
    return CommitInfo(
        total_commits=85000,
        commits_30_days=500,
        commits_90_days=1500,
        frequency="daily",
        last_commit_date=datetime(2025, 2, 4),
        first_commit_date=datetime(2016, 1, 14),
    )


@pytest.fixture
def sample_contributor_info():
    """Create sample ContributorInfo."""
    return ContributorInfo(
        total_contributors=450,
        top_contributors=["Soumith Chintala", "Edward Yang", "Nikita Shvetsov"],
        concentration_percentage=15.5,
        active_contributors=80,
        churn_rate=0.12,
    )


@pytest.fixture
def sample_dependency_info():
    """Create sample DependencyInfo."""
    return DependencyInfo(
        has_requirements_file=True,
        file_type="setuptools",
        total_dependencies=25,
        vulnerable_count=3,
    )


@pytest.fixture
def sample_testing_info():
    """Create sample TestingInfo."""
    return TestingInfo(
        has_tests=True,
        test_framework="pytest",
        ci_cd_type="github_actions",
        estimated_coverage=78.5,
    )


@pytest.fixture
def sample_documentation_info():
    """Create sample DocumentationInfo."""
    return DocumentationInfo(
        has_readme=True,
        has_contributing=True,
        has_code_of_conduct=False,
        has_architecture_docs=True,
        documentation_quality=82.0,
        readme_size_bytes=5000,
        contributing_size_bytes=2000,
    )


@pytest.fixture
def sample_repository_data(
    sample_repository_info,
    sample_commit_info,
    sample_contributor_info,
    sample_dependency_info,
    sample_testing_info,
    sample_documentation_info,
):
    """Create complete RepositoryData."""
    return RepositoryData(
        repo_info=sample_repository_info,
        commits=sample_commit_info,
        contributors=sample_contributor_info,
        dependencies=sample_dependency_info,
        testing=sample_testing_info,
        documentation=sample_documentation_info,
        fetched_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_audit_finding():
    """Create sample AuditFinding."""
    return AuditFindingModel(
        category="Code Quality",
        severity="HIGH",
        title="Low test coverage",
        description="Test coverage is below 80% threshold",
        recommendation="Add tests for critical paths",
        affected_items=["src/models.py", "src/utils.py"],
        estimation_hours=40,
        evidence="Coverage report shows 67% coverage",
    )


# ===== DATABASE ENTITY FIXTURES =====

@pytest.fixture
async def sample_db_repository(test_db_session):
    """Create sample Repository in database."""
    repo = Repository(
        owner="pytorch",
        repo="pytorch",
        url="https://github.com/pytorch/pytorch",
        description="Tensors and Dynamic neural networks",
        language="C++",
        license="BSD-3-Clause",
        stars=65000,
        forks=18000,
        open_issues=5000,
    )
    test_db_session.add(repo)
    await test_db_session.commit()
    return repo


@pytest.fixture
async def sample_db_audit(test_db_session, sample_db_repository):
    """Create sample Audit in database."""
    audit = Audit(
        audit_id="a1b2c3d4",
        repository_id=sample_db_repository.id,
        overall_score=75.5,
        ip_legal_score=72.0,
        team_score=68.0,
        code_quality_score=78.0,
        security_score=80.0,
        status="COMPLETED",
        go_no_go="CAUTION",
        technical_debt_cost=50000.0,
        compliance_risk_cost=10000.0,
        security_risk_cost=15000.0,
        team_risk_cost=5000.0,
        total_risk_usd=80000.0,
        valuation_discount_percent=8.0,
        executive_summary="Audit shows moderate risk",
        red_flags=["Low test coverage", "High bus factor"],
        critical_findings_count=2,
    )
    test_db_session.add(audit)
    await test_db_session.commit()
    return audit


@pytest.fixture
async def sample_db_finding(test_db_session, sample_db_audit):
    """Create sample AuditFinding in database."""
    finding = AuditFinding(
        audit_id=sample_db_audit.id,
        category="Code Quality",
        severity="HIGH",
        title="Low test coverage",
        description="Test coverage below 80%",
        recommendation="Add tests for critical paths",
        affected_items=["src/models.py"],
        estimation_hours=40,
    )
    test_db_session.add(finding)
    await test_db_session.commit()
    return finding


# ===== SETTINGS FIXTURES =====

@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        environment="test",
        debug=True,
        api_host="127.0.0.1",
        api_port=8000,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        github_token="test_token_123",
    )


# ===== UTILITY FIXTURES =====

@pytest.fixture
def github_api_responses():
    """Mock GitHub API responses."""
    return {
        "repository": {
            "owner": "pytorch",
            "name": "pytorch",
            "description": "Tensors and Dynamic neural networks",
            "language": "C++",
            "stargazers_count": 65000,
            "forks_count": 18000,
            "open_issues_count": 5000,
        },
        "commits": [
            {
                "commit": {
                    "message": "Fix memory leak in CUDA backend",
                    "author": {"date": "2024-01-15T10:30:00Z", "name": "Edward Yang"}
                },
                "author": {"login": "ezyang", "contributions": 1200}
            },
            {
                "commit": {
                    "message": "Add type hints to core modules",
                    "author": {"date": "2024-01-14T15:45:00Z", "name": "Soumith Chintala"}
                },
                "author": {"login": "soumith", "contributions": 950}
            }
        ],
        "contributors": [
            {"login": "ezyang", "contributions": 1200},
            {"login": "soumith", "contributions": 950},
            {"login": "user123", "contributions": 500}
        ],
        "dependencies": {
            "python": 15,
            "javascript": 3,
            "vulnerable": 2,
        },
        "pull_requests": [
            {"state": "open", "number": 123},
            {"state": "closed", "number": 122}
        ],
        "issues": [
            {"state": "open", "number": 500},
            {"state": "closed", "number": 499}
        ]
    }


# ===== API REQUEST/RESPONSE FIXTURES =====

@pytest.fixture
def sample_audit_request():
    """Create sample audit request."""
    return {
        "owner": "pytorch",
        "repo": "pytorch",
        "detailed_analysis": True
    }


@pytest.fixture
def sample_audit_response():
    """Create sample audit response."""
    return {
        "audit_id": "a1b2c3d4",
        "status": "PROCESSING",
        "owner": "pytorch",
        "repo": "pytorch",
        "created_at": "2024-01-15T10:00:00Z",
        "estimated_completion": "2024-01-15T11:00:00Z"
    }
