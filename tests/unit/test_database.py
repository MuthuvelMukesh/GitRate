"""Unit tests for database layer."""

import pytest
from datetime import datetime

from core.database import Repository, Audit, AuditFinding, AuditCache, GitHubMetrics


@pytest.mark.asyncio
class TestRepositoryModel:
    """Tests for Repository database model."""
    
    async def test_create_repository(self, test_db_session, sample_db_repository):
        """Test creating repository record."""
        assert sample_db_repository.owner == "pytorch"
        assert sample_db_repository.repo == "pytorch"
        assert sample_db_repository.stars == 65000
    
    async def test_repository_timestamps(self, sample_db_repository):
        """Test repository timestamps."""
        assert isinstance(sample_db_repository.created_at, datetime)
        assert isinstance(sample_db_repository.updated_at, datetime)
        assert sample_db_repository.created_at <= sample_db_repository.updated_at
    
    async def test_repository_defaults(self, test_db_session):
        """Test repository default values."""
        repo = Repository(
            owner="test",
            repo="test",
            url="https://github.com/test/test",
        )
        test_db_session.add(repo)
        await test_db_session.commit()
        
        assert repo.stars == 0
        assert repo.forks == 0
        assert repo.open_issues == 0


@pytest.mark.asyncio
class TestAuditModel:
    """Tests for Audit database model."""
    
    async def test_create_audit(self, test_db_session, sample_db_audit):
        """Test creating audit record."""
        assert sample_db_audit.audit_id == "a1b2c3d4"
        assert sample_db_audit.overall_score == 75.5
        assert sample_db_audit.status == "COMPLETED"
    
    async def test_audit_financial_impact(self, sample_db_audit):
        """Test audit financial impact fields."""
        assert sample_db_audit.technical_debt_cost == 50000.0
        assert sample_db_audit.total_risk_usd == 80000.0
        assert 0 <= sample_db_audit.valuation_discount_percent <= 100
    
    async def test_audit_scores_range(self, test_db_session, sample_db_repository):
        """Test audit scores are in valid range."""
        audit = Audit(
            audit_id="score_test",
            repository_id=sample_db_repository.id,
            overall_score=0.0,      # Minimum
            ip_legal_score=100.0,   # Maximum
            team_score=50.0,
            code_quality_score=75.0,
            security_score=88.0,
        )
        test_db_session.add(audit)
        await test_db_session.commit()
        
        assert all(0 <= s <= 100 for s in [
            audit.overall_score,
            audit.ip_legal_score,
            audit.team_score,
            audit.code_quality_score,
            audit.security_score,
        ])
    
    async def test_audit_red_flags(self, sample_db_audit):
        """Test audit red flags list."""
        assert isinstance(sample_db_audit.red_flags, list)
        assert len(sample_db_audit.red_flags) == 2
        assert "Low test coverage" in sample_db_audit.red_flags


@pytest.mark.asyncio
class TestAuditFindingModel:
    """Tests for AuditFinding database model."""
    
    async def test_create_finding(self, test_db_session, sample_db_finding):
        """Test creating audit finding record."""
        assert sample_db_finding.category == "Code Quality"
        assert sample_db_finding.severity == "HIGH"
        assert sample_db_finding.estimation_hours == 40
    
    async def test_finding_affected_items(self, sample_db_finding):
        """Test finding affected items."""
        assert isinstance(sample_db_finding.affected_items, list)
        assert "src/models.py" in sample_db_finding.affected_items
    
    async def test_finding_severity_levels(self, test_db_session, sample_db_audit):
        """Test different severity levels."""
        severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        
        for severity in severities:
            finding = AuditFinding(
                audit_id=sample_db_audit.id,
                category="Test",
                severity=severity,
                title=f"Test {severity}",
                description="Test finding",
                recommendation="Test",
            )
            test_db_session.add(finding)
        
        await test_db_session.commit()
        
        # Verify all were created
        findings = await test_db_session.query(AuditFinding).filter(
            AuditFinding.audit_id == sample_db_audit.id
        ).all()
        assert len(findings) == 4


@pytest.mark.asyncio
class TestAuditCacheModel:
    """Tests for AuditCache database model."""
    
    async def test_create_cache_entry(self, test_db_session, sample_db_repository):
        """Test creating cache entry."""
        cache_entry = AuditCache(
            repository_id=sample_db_repository.id,
            cache_key="repo:pytorch/pytorch:data",
            cache_data={"owner": "pytorch", "stars": 65000},
            expires_at=datetime.utcnow(),
        )
        test_db_session.add(cache_entry)
        await test_db_session.commit()
        
        assert cache_entry.cache_key == "repo:pytorch/pytorch:data"
        assert cache_entry.ttl_seconds == 86400  # Default 24h


@pytest.mark.asyncio
class TestGitHubMetricsModel:
    """Tests for GitHubMetrics database model."""
    
    async def test_create_metrics(self, test_db_session, sample_db_repository):
        """Test creating GitHub metrics record."""
        metrics = GitHubMetrics(
            repository_id=sample_db_repository.id,
            metric_date=datetime.utcnow(),
            stars=65000,
            forks=18000,
            open_issues=5000,
            commits_total=85000,
            contributors_total=450,
            commit_frequency="daily",
            test_coverage=78.5,
            documentation_quality=82.0,
        )
        test_db_session.add(metrics)
        await test_db_session.commit()
        
        assert metrics.stars == 65000
        assert metrics.commit_frequency == "daily"


@pytest.mark.asyncio
class TestDatabaseRelationships:
    """Tests for database model relationships."""
    
    async def test_repository_audit_relationship(
        self,
        test_db_session,
        sample_db_repository,
        sample_db_audit
    ):
        """Test Repository-Audit one-to-many relationship."""
        # Reload to test relationship
        assert sample_db_audit.repository_id == sample_db_repository.id
        
        # Create second audit for same repo
        audit2 = Audit(
            audit_id="test2",
            repository_id=sample_db_repository.id,
            overall_score=80.0,
            ip_legal_score=75.0,
            team_score=80.0,
            code_quality_score=85.0,
            security_score=90.0,
        )
        test_db_session.add(audit2)
        await test_db_session.commit()
        
        # Verify both audits linked to repo
        audits = sample_db_repository.audits
        assert len(audits) == 2
    
    async def test_audit_finding_relationship(
        self,
        test_db_session,
        sample_db_audit,
        sample_db_finding
    ):
        """Test Audit-Finding one-to-many relationship."""
        assert sample_db_finding.audit_id == sample_db_audit.id
        
        # Create second finding
        finding2 = AuditFinding(
            audit_id=sample_db_audit.id,
            category="Security",
            severity="CRITICAL",
            title="Unpatched CVE",
            description="Critical vulnerability",
            recommendation="Update dependency",
        )
        test_db_session.add(finding2)
        await test_db_session.commit()
        
        # Verify both findings linked to audit
        findings = sample_db_audit.findings
        assert len(findings) == 2


@pytest.mark.asyncio
class TestDatabaseQueries:
    """Tests for database queries."""
    
    async def test_query_by_owner_repo(self, test_db_session, sample_db_repository):
        """Test querying repository by owner and repo."""
        from sqlalchemy import select
        
        stmt = select(Repository).where(
            (Repository.owner == "pytorch") &
            (Repository.repo == "pytorch")
        )
        result = await test_db_session.execute(stmt)
        repo = result.scalar_one_or_none()
        
        assert repo is not None
        assert repo.owner == "pytorch"
    
    async def test_query_audits_by_status(self, test_db_session, sample_db_audit):
        """Test querying audits by status."""
        from sqlalchemy import select
        
        stmt = select(Audit).where(Audit.status == "COMPLETED")
        result = await test_db_session.execute(stmt)
        audits = result.scalars().all()
        
        assert len(audits) >= 1
        assert all(a.status == "COMPLETED" for a in audits)
    
    async def test_query_findings_by_severity(self, test_db_session, sample_db_finding):
        """Test querying findings by severity."""
        from sqlalchemy import select
        
        stmt = select(AuditFinding).where(AuditFinding.severity == "HIGH")
        result = await test_db_session.execute(stmt)
        findings = result.scalars().all()
        
        assert len(findings) >= 1
        assert all(f.severity == "HIGH" for f in findings)
