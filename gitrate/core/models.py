"""Data models for GitRate using Pydantic."""

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator


# ===== REPOSITORY MODELS =====

class RepositoryInfo(BaseModel):
    """GitHub repository basic information."""
    
    owner: str = Field(..., description="Repository owner/organization")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/name)")
    url: HttpUrl = Field(..., description="Repository URL")
    description: Optional[str] = Field(None, description="Repository description")
    homepage: Optional[HttpUrl] = Field(None, description="Project homepage")
    
    stars: int = Field(default=0, ge=0, description="Star count")
    forks: int = Field(default=0, ge=0, description="Fork count")
    watchers: int = Field(default=0, ge=0, description="Watcher count")
    open_issues: int = Field(default=0, ge=0, description="Open issues count")
    
    language: Optional[str] = Field(None, description="Primary programming language")
    languages: Dict[str, int] = Field(default_factory=dict, description="All languages with LOC")
    
    license: Optional[str] = Field(None, description="License type")
    is_private: bool = Field(default=False, description="Whether repository is private")
    is_fork: bool = Field(default=False, description="Whether repository is a fork")
    
    created_at: datetime = Field(..., description="Repository creation date")
    updated_at: datetime = Field(..., description="Last update date")
    pushed_at: Optional[datetime] = Field(None, description="Last push date")
    
    size_kb: int = Field(default=0, ge=0, description="Repository size in KB")


class CommitInfo(BaseModel):
    """Commit statistics."""
    
    total_commits: int = Field(default=0, ge=0, description="Total commit count")
    commits_30days: int = Field(default=0, ge=0, description="Commits in last 30 days")
    commits_90days: int = Field(default=0, ge=0, description="Commits in last 90 days")
    
    last_commit_date: Optional[datetime] = Field(None, description="Date of last commit")
    first_commit_date: Optional[datetime] = Field(None, description="Date of first commit")
    
    commit_frequency: str = Field(default="unknown", description="Commit frequency (daily, weekly, etc)")


class ContributorInfo(BaseModel):
    """Contributor statistics."""
    
    total_contributors: int = Field(default=0, ge=0, description="Total contributor count")
    top_contributors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top contributors with commit counts"
    )
    
    contributor_concentration: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="% of commits by top contributor"
    )
    
    active_contributors_30days: int = Field(default=0, ge=0, description="Active in last 30 days")
    churn_rate: float = Field(default=0.0, description="Contributor churn rate")


class DependencyInfo(BaseModel):
    """Dependency and requirement information."""
    
    has_requirements: bool = Field(default=False, description="Has requirements.txt/package.json")
    dependency_file_type: Optional[str] = Field(None, description="Type of dependency file")
    
    total_dependencies: int = Field(default=0, ge=0, description="Total dependency count")
    outdated_dependencies: int = Field(default=0, ge=0, description="Outdated dependencies")
    
    vulnerable_dependencies: int = Field(default=0, ge=0, description="Dependencies with known CVEs")
    
    main_dependencies: List[str] = Field(default_factory=list, description="Top dependencies")


class TestingInfo(BaseModel):
    """Testing infrastructure information."""
    
    has_tests: bool = Field(default=False, description="Has test directory/files")
    test_framework: Optional[str] = Field(None, description="Detected test framework")
    
    has_ci_cd: bool = Field(default=False, description="Has CI/CD configuration")
    ci_cd_type: Optional[str] = Field(None, description="Type of CI/CD (GitHub Actions, etc)")
    
    estimated_coverage: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Estimated test coverage %"
    )


class DocumentationInfo(BaseModel):
    """Documentation and README information."""
    
    has_readme: bool = Field(default=False, description="Has README file")
    readme_length: int = Field(default=0, ge=0, description="README length in bytes")
    readme_snippet: Optional[str] = Field(None, description="First 500 chars of README")
    
    has_contributing: bool = Field(default=False, description="Has CONTRIBUTING.md")
    has_code_of_conduct: bool = Field(default=False, description="Has CODE_OF_CONDUCT.md")
    has_architecture_docs: bool = Field(default=False, description="Has architecture documentation")
    
    documentation_quality_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Documentation quality score"
    )


class RepositoryData(BaseModel):
    """Complete repository data collected."""
    
    repo_info: RepositoryInfo
    commits: CommitInfo
    contributors: ContributorInfo
    dependencies: DependencyInfo
    testing: TestingInfo
    documentation: DocumentationInfo
    
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="When data was fetched")
    
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw GitHub API response"
    )


# ===== AUDIT RESULT MODELS =====

class AuditFinding(BaseModel):
    """Single audit finding."""
    
    category: str = Field(..., description="Audit category")
    severity: str = Field(..., description="Severity level (LOW, MEDIUM, HIGH, CRITICAL)")
    title: str = Field(..., description="Finding title")
    description: str = Field(..., description="Detailed description")
    
    affected_items: Optional[List[str]] = Field(
        None,
        description="List of affected files/modules/packages"
    )
    
    recommendation: str = Field(..., description="Remediation recommendation")
    estimation_hours: Optional[int] = Field(None, ge=0, description="Hours to fix")
    
    evidence: Optional[Dict[str, Any]] = Field(None, description="Supporting evidence/data")


class AuditScores(BaseModel):
    """All audit scores (0-100)."""
    
    ip_legal: float = Field(default=0, ge=0, le=100, description="IP & Legal risk score")
    team_sustainability: float = Field(default=0, ge=0, le=100, description="Team sustainability score")
    code_quality: float = Field(default=0, ge=0, le=100, description="Code quality score")
    security: float = Field(default=0, ge=0, le=100, description="Security score")
    
    overall: float = Field(default=0, ge=0, le=100, description="Overall audit score")


class FinancialImpact(BaseModel):
    """Financial impact of technical issues."""
    
    technical_debt_cost_usd: float = Field(default=0, ge=0, description="Cost to fix technical debt")
    compliance_risk_cost_usd: float = Field(default=0, ge=0, description="Potential compliance costs")
    security_risk_cost_usd: float = Field(default=0, ge=0, description="Potential security breach costs")
    team_risk_cost_usd: float = Field(default=0, ge=0, description="Team retention/training costs")
    
    total_risk_usd: float = Field(default=0, ge=0, description="Total financial risk")
    valuation_discount_percent: float = Field(default=0, ge=0, le=100, description="% discount on valuation")


class ComplianceCertificate(BaseModel):
    """Compliance certification results."""
    
    legal_compliance: str = Field(..., description="Legal compliance (RED, YELLOW, GREEN)")
    security_compliance: str = Field(..., description="Security compliance status")
    team_sustainability: str = Field(..., description="Team sustainability status")
    code_quality: str = Field(..., description="Code quality compliance")
    
    overall_compliance: str = Field(..., description="Overall compliance status")
    certification_date: datetime = Field(default_factory=datetime.utcnow)


class RoadmapTask(BaseModel):
    """90-day roadmap task."""
    
    phase: int = Field(..., ge=1, le=3, description="Phase (1=weeks 1-2, 2=weeks 3-6, 3=weeks 7-12)")
    week_range: str = Field(..., description="Week range (e.g., '1-2')")
    
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    
    estimated_hours: int = Field(..., ge=1, description="Estimated hours to complete")
    owner_role: str = Field(..., description="Owner role (Frontend, Backend, DevOps, etc)")
    
    dependencies: List[str] = Field(default_factory=list, description="Dependent task IDs")
    success_criteria: str = Field(..., description="Definition of done")
    
    priority: str = Field(default="MEDIUM", description="Task priority")


class AcquisitionAuditResult(BaseModel):
    """Complete acquisition audit result."""
    
    # Metadata
    audit_id: str = Field(..., description="Unique audit identifier")
    repository: str = Field(..., description="Repository identifier (owner/name)")
    
    audit_date: datetime = Field(default_factory=datetime.utcnow, description="Audit date")
    audit_duration_seconds: int = Field(default=0, ge=0, description="Audit execution time")
    
    # Scores
    scores: AuditScores = Field(..., description="Audit scores")
    
    # Findings
    findings: List[AuditFinding] = Field(default_factory=list, description="All audit findings")
    critical_findings: List[AuditFinding] = Field(default_factory=list, description="Critical findings only")
    
    red_flags: List[str] = Field(default_factory=list, description="Top 5 red flags")
    
    # Financial
    financial_impact: FinancialImpact = Field(default_factory=FinancialImpact, description="Financial impact")
    
    # Compliance
    compliance: ComplianceCertificate = Field(..., description="Compliance certificate")
    
    # Recommendations
    executive_summary: str = Field(..., description="1-paragraph executive summary")
    go_no_go_recommendation: str = Field(..., description="Recommendation (GO / CAUTION / NO_GO)")
    
    roadmap_90_day: List[RoadmapTask] = Field(default_factory=list, description="90-day roadmap")
    
    # Raw data
    repository_data: RepositoryData = Field(..., description="Collected repository data")
    
    
    class Config:
        json_schema_extra = {
            "example": {
                "audit_id": "audit-abc123",
                "repository": "owner/repo",
            }
        }


# ===== API REQUEST/RESPONSE MODELS =====

class AuditRequest(BaseModel):
    """Request to start an audit."""
    
    repository_url: str = Field(..., description="GitHub repository URL")
    include_detailed_analysis: bool = Field(default=True, description="Include detailed analysis")


class AuditResponse(BaseModel):
    """Response with audit results."""
    
    success: bool = Field(..., description="Whether audit was successful")
    audit_id: str = Field(..., description="Audit identifier")
    status: str = Field(..., description="Status (PENDING, IN_PROGRESS, COMPLETED, FAILED)")
    message: Optional[str] = Field(None, description="Status message")
    
    result: Optional[AcquisitionAuditResult] = Field(None, description="Audit results")
    error: Optional[str] = Field(None, description="Error message if failed")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Dict[str, str] = Field(default_factory=dict, description="Status of each service")
