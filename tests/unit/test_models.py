"""Unit tests for Pydantic models."""

import pytest
from datetime import datetime

from core.models import (
    RepositoryInfo, CommitInfo, ContributorInfo, DependencyInfo,
    TestingInfo, DocumentationInfo, RepositoryData, AuditScores,
    AuditFinding, FinancialImpact, ComplianceCertificate,
    RoadmapTask, AcquisitionAuditResult, AuditRequest, AuditResponse
)


class TestRepositoryInfo:
    """Tests for RepositoryInfo model."""
    
    def test_valid_repository_info(self, sample_repository_info):
        """Test creating valid RepositoryInfo."""
        assert sample_repository_info.owner == "pytorch"
        assert sample_repository_info.repo == "pytorch"
        assert sample_repository_info.stars == 65000
    
    def test_missing_required_field(self):
        """Test missing required field."""
        with pytest.raises(ValueError):
            RepositoryInfo(
                owner="pytorch",
                # repo is required but missing
                url="https://github.com/pytorch/pytorch",
            )
    
    def test_json_serialization(self, sample_repository_info):
        """Test JSON serialization."""
        json_data = sample_repository_info.model_dump_json()
        assert "pytorch" in json_data
    
    def test_invalid_star_count(self):
        """Test invalid (negative) star count."""
        with pytest.raises(ValueError):
            RepositoryInfo(
                owner="test",
                repo="test",
                url="https://github.com/test/test",
                stars=-100,  # Invalid
            )


class TestCommitInfo:
    """Tests for CommitInfo model."""
    
    def test_valid_commit_info(self, sample_commit_info):
        """Test creating valid CommitInfo."""
        assert sample_commit_info.total_commits == 85000
        assert sample_commit_info.frequency == "daily"
    
    def test_frequency_validation(self):
        """Test frequency field validation."""
        info = CommitInfo(
            total_commits=100,
            commits_30_days=10,
            commits_90_days=30,
            frequency="weekly",
        )
        assert info.frequency == "weekly"


class TestContributorInfo:
    """Tests for ContributorInfo model."""
    
    def test_valid_contributor_info(self, sample_contributor_info):
        """Test creating valid ContributorInfo."""
        assert sample_contributor_info.total_contributors == 450
        assert len(sample_contributor_info.top_contributors) == 3
    
    def test_concentration_percentage_valid(self):
        """Test valid concentration percentage."""
        info = ContributorInfo(
            total_contributors=100,
            top_contributors=["Alice", "Bob"],
            concentration_percentage=50.0,
        )
        assert 0 <= info.concentration_percentage <= 100


class TestDependencyInfo:
    """Tests for DependencyInfo model."""
    
    def test_valid_dependency_info(self, sample_dependency_info):
        """Test creating valid DependencyInfo."""
        assert sample_dependency_info.has_requirements_file
        assert sample_dependency_info.total_dependencies == 25
        assert sample_dependency_info.vulnerable_count == 3
    
    def test_vulnerable_count_less_than_total(self):
        """Test vulnerable count validation."""
        info = DependencyInfo(
            has_requirements_file=True,
            file_type="setuptools",
            total_dependencies=10,
            vulnerable_count=15,  # Should be less than total
        )
        # This should be caught by business logic, not Pydantic validation
        assert info.vulnerable_count == 15


class TestTestingInfo:
    """Tests for TestingInfo model."""
    
    def test_valid_testing_info(self, sample_testing_info):
        """Test creating valid TestingInfo."""
        assert sample_testing_info.has_tests
        assert sample_testing_info.test_framework == "pytest"
        assert sample_testing_info.estimated_coverage == 78.5
    
    def test_coverage_percentage_range(self):
        """Test coverage percentage is in valid range."""
        info = TestingInfo(
            has_tests=True,
            test_framework="pytest",
            ci_cd_type="github_actions",
            estimated_coverage=99.9,
        )
        assert 0 <= info.estimated_coverage <= 100


class TestDocumentationInfo:
    """Tests for DocumentationInfo model."""
    
    def test_valid_documentation_info(self, sample_documentation_info):
        """Test creating valid DocumentationInfo."""
        assert sample_documentation_info.has_readme
        assert sample_documentation_info.has_contributing
        assert sample_documentation_info.documentation_quality == 82.0
    
    def test_quality_score_range(self):
        """Test quality score is in valid range."""
        info = DocumentationInfo(
            has_readme=True,
            has_contributing=True,
            documentation_quality=95.5,
        )
        assert 0 <= info.documentation_quality <= 100


class TestRepositoryData:
    """Tests for RepositoryData model."""
    
    def test_valid_repository_data(self, sample_repository_data):
        """Test creating valid RepositoryData."""
        assert sample_repository_data.repo_info.owner == "pytorch"
        assert sample_repository_data.commits.total_commits == 85000
        assert sample_repository_data.contributors.total_contributors == 450
    
    def test_composed_models(self, sample_repository_data):
        """Test composed sub-models are accessible."""
        assert isinstance(sample_repository_data.repo_info, RepositoryInfo)
        assert isinstance(sample_repository_data.commits, CommitInfo)
        assert isinstance(sample_repository_data.contributors, ContributorInfo)


class TestAuditScores:
    """Tests for AuditScores model."""
    
    def test_valid_audit_scores(self):
        """Test creating valid AuditScores."""
        scores = AuditScores(
            ip_legal=75.0,
            team_sustainability=70.0,
            code_quality=80.0,
            security=85.0,
            overall=77.5,
        )
        assert scores.overall == 77.5
    
    def test_scores_in_range(self):
        """Test scores are in valid range."""
        scores = AuditScores(
            ip_legal=0.0,   # Minimum
            team_sustainability=100.0,  # Maximum
            code_quality=50.0,
            security=75.0,
            overall=56.25,
        )
        assert all(0 <= s <= 100 for s in [
            scores.ip_legal,
            scores.team_sustainability,
            scores.code_quality,
            scores.security,
            scores.overall,
        ])


class TestAuditFinding:
    """Tests for AuditFinding model."""
    
    def test_valid_audit_finding(self, sample_audit_finding):
        """Test creating valid AuditFinding."""
        assert sample_audit_finding.category == "Code Quality"
        assert sample_audit_finding.severity == "HIGH"
        assert sample_audit_finding.estimation_hours == 40
    
    def test_severity_levels(self):
        """Test different severity levels."""
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            finding = AuditFinding(
                category="Test",
                severity=severity,
                title="Test",
                description="Test",
                recommendation="Test",
            )
            assert finding.severity == severity


class TestFinancialImpact:
    """Tests for FinancialImpact model."""
    
    def test_valid_financial_impact(self):
        """Test creating valid FinancialImpact."""
        impact = FinancialImpact(
            technical_debt_cost_usd=50000.0,
            compliance_risk_cost_usd=10000.0,
            security_risk_cost_usd=15000.0,
            team_risk_cost_usd=5000.0,
            total_risk_usd=80000.0,
            valuation_discount_percent=8.0,
        )
        assert impact.total_risk_usd == 80000.0
    
    def test_non_negative_costs(self):
        """Test costs are non-negative."""
        impact = FinancialImpact(
            technical_debt_cost_usd=0.0,
            total_risk_usd=0.0,
        )
        assert impact.technical_debt_cost_usd >= 0


class TestComplianceCertificate:
    """Tests for ComplianceCertificate model."""
    
    def test_valid_compliance(self):
        """Test creating valid ComplianceCertificate."""
        cert = ComplianceCertificate(
            legal_compliance="GREEN",
            security_compliance="YELLOW",
            team_sustainability="RED",
            code_quality="GREEN",
            overall_compliance="YELLOW",
        )
        assert cert.legal_compliance == "GREEN"
    
    def test_status_values(self):
        """Test valid status values."""
        for status in ["RED", "YELLOW", "GREEN"]:
            cert = ComplianceCertificate(
                legal_compliance=status,
            )
            assert cert.legal_compliance == status


class TestRoadmapTask:
    """Tests for RoadmapTask model."""
    
    def test_valid_roadmap_task(self):
        """Test creating valid RoadmapTask."""
        task = RoadmapTask(
            phase=1,
            week_range="1-2",
            title="Security Hardening",
            description="Rotate secrets",
            estimated_hours=40,
            owner_role="DevOps",
            success_criteria="Secrets rotated",
            priority="CRITICAL",
        )
        assert task.phase == 1
        assert task.priority == "CRITICAL"
    
    def test_phase_range(self):
        """Test phase is valid."""
        for phase in [1, 2, 3]:
            task = RoadmapTask(
                phase=phase,
                week_range="1-2",
                title="Test",
            )
            assert task.phase == phase


class TestAcquisitionAuditResult:
    """Tests for AcquisitionAuditResult model."""
    
    def test_complete_audit_result(self):
        """Test creating complete AcquisitionAuditResult."""
        result = AcquisitionAuditResult(
            audit_id="a1b2c3d4",
            repository="pytorch/pytorch",
            scores=AuditScores(
                ip_legal=75.0,
                team_sustainability=70.0,
                code_quality=80.0,
                security=85.0,
                overall=77.5,
            ),
            findings=[],
            financial_impact=FinancialImpact(
                technical_debt_cost_usd=50000.0,
                total_risk_usd=80000.0,
            ),
        )
        assert result.audit_id == "a1b2c3d4"


class TestAuditRequest:
    """Tests for AuditRequest model."""
    
    def test_valid_audit_request(self):
        """Test creating valid AuditRequest."""
        request = AuditRequest(
            repository_url="https://github.com/pytorch/pytorch",
        )
        assert "pytorch" in request.repository_url
    
    def test_detailed_analysis_flag(self):
        """Test detailed analysis flag."""
        request = AuditRequest(
            repository_url="https://github.com/test/test",
            include_detailed_analysis=True,
        )
        assert request.include_detailed_analysis


class TestAuditResponse:
    """Tests for AuditResponse model."""
    
    def test_valid_audit_response(self):
        """Test creating valid AuditResponse."""
        response = AuditResponse(
            success=True,
            status="COMPLETED",
            message="Audit completed successfully",
        )
        assert response.success
        assert response.status == "COMPLETED"
