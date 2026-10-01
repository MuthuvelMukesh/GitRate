"""Integration tests for end-to-end audit flow."""

import pytest
from datetime import datetime

from gitrate.core.audit_engine import AuditEngine
from gitrate.core.models import RepositoryData
from gitrate.integrations.repo_fetcher import CachedRepositoryFetcher


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuditFlow:
    """Integration tests for complete audit flow."""
    
    async def test_audit_initialization(self):
        """Test AuditEngine initialization."""
        engine = AuditEngine(github_token="test_token")
        assert engine.github_token == "test_token"
        assert isinstance(engine.active_audits, dict)
    
    async def test_audit_status_tracking(self):
        """Test audit status tracking."""
        engine = AuditEngine()
        audit_id = "test123"
        
        # Start tracking
        engine.active_audits[audit_id] = {
            "status": "IN_PROGRESS",
            "owner": "test",
            "repo": "test",
        }
        
        assert audit_id in engine.active_audits
        assert engine.active_audits[audit_id]["status"] == "IN_PROGRESS"
    
    async def test_cached_fetcher_initialization(self, mock_redis_cache):
        """Test CachedRepositoryFetcher initialization."""
        fetcher = CachedRepositoryFetcher(
            github_token="test_token",
            cache=mock_redis_cache,
        )
        
        assert fetcher.cache is not None
        assert fetcher.cache_ttl_seconds == 86400


@pytest.mark.integration
@pytest.mark.asyncio
class TestCachedFetcher:
    """Integration tests for cached repository fetcher."""
    
    async def test_cache_storing_and_retrieval(
        self,
        mock_redis_cache,
        sample_repository_data,
    ):
        """Test caching and retrieving repository data."""
        from gitrate.core.cache import CacheKeys
        
        fetcher = CachedRepositoryFetcher(
            cache=mock_redis_cache,
            cache_ttl_seconds=3600,
        )
        
        cache_key = CacheKeys.repo_data("pytorch", "pytorch")
        cache_dict = sample_repository_data.model_dump()
        cache_dict['fetched_at'] = str(sample_repository_data.fetched_at)
        
        # Store in cache
        await fetcher.cache.set(cache_key, cache_dict)
        
        # Retrieve from cache
        cached = await fetcher.cache.get(cache_key)
        assert cached is not None
        assert cached["repo_info"]["owner"] == "pytorch"
    
    async def test_cache_invalidation(self, mock_redis_cache):
        """Test cache invalidation."""
        fetcher = CachedRepositoryFetcher(cache=mock_redis_cache)
        
        # Set cache entry
        await fetcher.cache.set("repo:pytorch/pytorch:data", {"data": "test"})
        
        # Verify exists
        exists = await fetcher.cache.exists("repo:pytorch/pytorch:data")
        assert exists is True
        
        # Clear cache
        success = await fetcher.clear_cache("pytorch", "pytorch")
        assert success is True
        
        # Verify deleted
        exists = await fetcher.cache.exists("repo:pytorch/pytorch:data")
        assert exists is False


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuditEngineStubs:
    """Integration tests for audit engine with stub auditors."""
    
    async def test_ip_legal_audit_stub(self):
        """Test IP & Legal audit stub."""
        engine = AuditEngine()
        from gitrate.core.models import RepositoryData, RepositoryInfo
        
        repo_data = RepositoryData(
            repo_info=RepositoryInfo(
                owner="test",
                repo="test",
                url="https://github.com/test/test",
            ),
            commits=None,
            contributors=None,
            dependencies=None,
            testing=None,
            documentation=None,
        )
        
        score, findings = await engine._audit_ip_legal(repo_data)
        
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert isinstance(findings, list)
    
    async def test_team_audit_stub(self):
        """Test Team Sustainability audit stub."""
        engine = AuditEngine()
        from gitrate.core.models import (
            RepositoryData, RepositoryInfo, ContributorInfo
        )
        
        repo_data = RepositoryData(
            repo_info=RepositoryInfo(
                owner="test",
                repo="test",
                url="https://github.com/test/test",
            ),
            contributors=ContributorInfo(
                total_contributors=2,  # Low count
                top_contributors=["Alice"],
                concentration_percentage=50.0,
            ),
            commits=None,
            dependencies=None,
            testing=None,
            documentation=None,
        )
        
        score, findings = await engine._audit_team_sustainability(repo_data)
        
        assert isinstance(score, float)
        assert isinstance(findings, list)
        # Low contributor count should generate finding
        assert len(findings) > 0
    
    async def test_code_quality_audit_stub(self):
        """Test Code Quality audit stub."""
        engine = AuditEngine()
        from gitrate.core.models import (
            RepositoryData, RepositoryInfo, TestingInfo,
            DocumentationInfo
        )
        
        repo_data = RepositoryData(
            repo_info=RepositoryInfo(
                owner="test",
                repo="test",
                url="https://github.com/test/test",
            ),
            testing=TestingInfo(
                has_tests=False,  # No tests
                test_framework=None,
            ),
            documentation=DocumentationInfo(
                has_readme=False,  # No docs
            ),
            commits=None,
            contributors=None,
            dependencies=None,
        )
        
        score, findings = await engine._audit_code_quality(repo_data)
        
        assert isinstance(score, float)
        assert isinstance(findings, list)
        # Missing tests and README should generate findings
        assert len(findings) >= 2
    
    async def test_security_audit_stub(self):
        """Test Security audit stub."""
        engine = AuditEngine()
        from gitrate.core.models import RepositoryData, RepositoryInfo
        
        repo_data = RepositoryData(
            repo_info=RepositoryInfo(
                owner="test",
                repo="test",
                url="https://github.com/test/test",
            ),
            commits=None,
            contributors=None,
            dependencies=None,
            testing=None,
            documentation=None,
        )
        
        score, findings = await engine._audit_security(repo_data)
        
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert isinstance(findings, list)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuditEngineHelpers:
    """Integration tests for audit engine helper methods."""
    
    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        engine = AuditEngine()
        
        scores = {
            "ip_legal": 75.0,
            "security": 85.0,
            "code_quality": 80.0,
            "team_sustainability": 70.0,
        }
        
        overall = engine._calculate_overall_score(scores)
        
        # Weighted average: (75*0.30 + 85*0.25 + 80*0.25 + 70*0.20) / 1.0
        assert isinstance(overall, float)
        assert 0 <= overall <= 100
        assert 75 <= overall <= 81  # Expected range
    
    def test_generate_compliance_certificate(self):
        """Test compliance certificate generation."""
        engine = AuditEngine()
        
        scores = {
            "ip_legal": 85.0,
            "security": 60.0,
            "code_quality": 55.0,
            "team_sustainability": 45.0,
        }
        findings = []  # No critical findings
        
        cert = engine._generate_compliance_certificate(scores, findings)
        
        assert cert.legal_compliance == "GREEN"
        assert cert.security_compliance == "YELLOW"
        assert cert.code_quality == "YELLOW"
    
    def test_calculate_financial_impact(self):
        """Test financial impact calculation."""
        engine = AuditEngine()
        from gitrate.core.models import AuditFinding as AuditFindingModel, RepositoryData, RepositoryInfo
        
        findings = [
            AuditFindingModel(
                category="Test",
                severity="CRITICAL",
                title="Critical issue",
                estimation_hours=100,
            ),
            AuditFindingModel(
                category="Test",
                severity="HIGH",
                title="High issue",
                estimation_hours=50,
            ),
        ]
        
        repo_data = RepositoryData(
            repo_info=RepositoryInfo(
                owner="test",
                repo="test",
                url="https://github.com/test/test",
            ),
            contributors=None,
            commits=None,
            dependencies=None,
            testing=None,
            documentation=None,
        )
        
        impact = engine._calculate_financial_impact(findings, repo_data)
        
        # 150 hours * $100/hour = $15,000 base
        assert impact.technical_debt_cost_usd >= 10000
        assert impact.total_risk_usd >= 10000
        assert 0 <= impact.valuation_discount_percent <= 30
    
    def test_generate_90day_roadmap(self):
        """Test 90-day roadmap generation."""
        engine = AuditEngine()
        
        findings = []
        roadmap = engine._generate_90day_roadmap(findings)
        
        assert isinstance(roadmap, list)
        assert len(roadmap) >= 3
        
        # Verify roadmap structure
        for task in roadmap:
            assert task.phase in [1, 2, 3]
            assert task.week_range is not None
            assert task.estimated_hours > 0
    
    def test_extract_red_flags(self):
        """Test red flag extraction."""
        engine = AuditEngine()
        from gitrate.core.models import AuditFinding as AuditFindingModel
        
        findings = [
            AuditFindingModel(
                category="Test",
                severity="CRITICAL",
                title="Critical issue 1",
            ),
            AuditFindingModel(
                category="Test",
                severity="CRITICAL",
                title="Critical issue 2",
            ),
            AuditFindingModel(
                category="Test",
                severity="HIGH",
                title="High issue",
            ),
        ]
        
        red_flags = engine._extract_red_flags(findings)
        
        assert isinstance(red_flags, list)
        assert len(red_flags) <= 5
        assert "Critical issue 1" in red_flags or "Critical issue 2" in red_flags
    
    def test_determine_go_no_go(self):
        """Test go/no-go determination."""
        engine = AuditEngine()
        
        # Good scores - should be GO
        good_scores = {
            "ip_legal": 85.0,
            "security": 90.0,
            "code_quality": 85.0,
            "team_sustainability": 80.0,
        }
        
        recommendation = engine._determine_go_no_go(good_scores, [])
        assert recommendation == "GO"
        
        # Mediocre scores - should be CAUTION
        medium_scores = {
            "ip_legal": 70.0,
            "security": 65.0,
            "code_quality": 70.0,
            "team_sustainability": 60.0,
        }
        
        recommendation = engine._determine_go_no_go(medium_scores, [])
        assert recommendation == "CAUTION"
        
        # Poor scores - should be NO_GO
        bad_scores = {
            "ip_legal": 40.0,
            "security": 35.0,
            "code_quality": 40.0,
            "team_sustainability": 30.0,
        }
        
        recommendation = engine._determine_go_no_go(bad_scores, [])
        assert recommendation == "NO_GO"
