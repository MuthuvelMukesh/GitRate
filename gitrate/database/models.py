"""SQLAlchemy database models and async session management."""

from datetime import datetime
from typing import Optional, List
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime,
    Boolean, ForeignKey, JSON, Index, create_engine
)
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base, relationship

from gitrate.utils.config import settings

# Create async engine and session factory
Base = declarative_base()


async def get_database_engine() -> AsyncEngine:
    """Create async database engine."""
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=settings.db_pool_size,
        max_overflow=10,
        pool_pre_ping=True,
    )


async def get_session_factory(engine: AsyncEngine):
    """Create async session factory."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


# Global session factory (initialized at app startup)
SessionLocal = None


async def init_db():
    """Initialize database (create tables)."""
    engine = await get_database_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def get_db() -> AsyncSession:
    """Get database session dependency for FastAPI."""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    async with SessionLocal() as session:
        yield session


# ===== DATABASE MODELS =====

class Repository(Base):
    """GitHub repository record."""
    __tablename__ = "repositories"
    __table_args__ = (
        Index('idx_owner_repo', 'owner', 'repo', unique=True),
        Index('idx_last_fetched', 'last_fetched_at'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner = Column(String(255), nullable=False)
    repo = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    
    # Repo info
    description = Column(Text, nullable=True)
    language = Column(String(50), nullable=True)
    license = Column(String(100), nullable=True)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_fetched_at = Column(DateTime, nullable=True)
    
    # Relationships
    audits = relationship("Audit", back_populates="repository", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Repository {self.owner}/{self.repo}>"


class Audit(Base):
    """Acquisition audit record."""
    __tablename__ = "audits"
    __table_args__ = (
        Index('idx_repository_id', 'repository_id'),
        Index('idx_audit_date', 'audit_date'),
        Index('idx_status', 'status'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_id = Column(String(8), unique=True, nullable=False)  # Short ID for API
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    
    # Scores
    overall_score = Column(Float, nullable=False)
    ip_legal_score = Column(Float, nullable=False)
    team_score = Column(Float, nullable=False)
    code_quality_score = Column(Float, nullable=False)
    security_score = Column(Float, nullable=False)
    
    # Status
    status = Column(String(20), default="COMPLETED")  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    go_no_go = Column(String(20), default="CAUTION")  # GO, CAUTION, NO_GO
    
    # Financial impact
    technical_debt_cost = Column(Float, default=0.0)
    compliance_risk_cost = Column(Float, default=0.0)
    security_risk_cost = Column(Float, default=0.0)
    team_risk_cost = Column(Float, default=0.0)
    total_risk_usd = Column(Float, default=0.0)
    valuation_discount_percent = Column(Float, default=0.0)
    
    # Summary
    executive_summary = Column(Text, nullable=True)
    red_flags = Column(JSON, default=list)  # JSON list of top 5 red flags
    critical_findings_count = Column(Integer, default=0)
    
    # Timestamps
    audit_date = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Relationships
    repository = relationship("Repository", back_populates="audits")
    findings = relationship("AuditFinding", back_populates="audit", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Audit {self.audit_id} score={self.overall_score}>"


class AuditFinding(Base):
    """Individual audit finding/issue."""
    __tablename__ = "audit_findings"
    __table_args__ = (
        Index('idx_audit_id', 'audit_id'),
        Index('idx_severity', 'severity'),
        Index('idx_category', 'category'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_id = Column(String(36), ForeignKey("audits.id"), nullable=False)
    
    # Finding details
    category = Column(String(50), nullable=False)  # IP_Legal, Team, CodeQuality, Security
    severity = Column(String(20), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    
    # Impact
    affected_items = Column(JSON, default=list)  # JSON list of affected files/components
    estimation_hours = Column(Integer, default=0)
    evidence = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    audit = relationship("Audit", back_populates="findings")
    
    def __repr__(self):
        return f"<Finding {self.category}/{self.severity}: {self.title}>"


class AuditCache(Base):
    """Cache for audit results."""
    __tablename__ = "audit_cache"
    __table_args__ = (
        Index('idx_repository_id', 'repository_id'),
        Index('idx_expires_at', 'expires_at'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    
    # Cached data (JSON)
    cache_key = Column(String(255), unique=True, nullable=False)
    cache_data = Column(JSON, nullable=False)
    
    # Cache control
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    ttl_seconds = Column(Integer, default=86400)  # 24 hours default
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<AuditCache {self.cache_key}>"


class GitHubMetrics(Base):
    """Historical GitHub metrics for repositories."""
    __tablename__ = "github_metrics"
    __table_args__ = (
        Index('idx_repository_id', 'repository_id'),
        Index('idx_metric_date', 'metric_date'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    
    # Metrics
    metric_date = Column(DateTime, default=datetime.utcnow)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    commits_total = Column(Integer, default=0)
    contributors_total = Column(Integer, default=0)
    
    # Derived metrics
    commit_frequency = Column(String(50), nullable=True)  # stale, monthly, weekly, daily, multiple_daily
    test_coverage = Column(Float, nullable=True)
    documentation_quality = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<GitHubMetrics {self.repository_id} @ {self.metric_date}>"


class VulnerabilityCache(Base):
    """Cache of known vulnerabilities."""
    __tablename__ = "vulnerability_cache"
    __table_args__ = (
        Index('idx_cve_id', 'cve_id', unique=True),
        Index('idx_package_name', 'package_name'),
        Index('idx_expires_at', 'expires_at'),
    )
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Vulnerability info
    cve_id = Column(String(50), nullable=False)
    package_name = Column(String(255), nullable=False)
    package_version = Column(String(100), nullable=True)
    severity = Column(String(20))  # CRITICAL, HIGH, MEDIUM, LOW
    
    # Details
    description = Column(Text, nullable=True)
    cvss_score = Column(Float, nullable=True)
    published_date = Column(DateTime, nullable=True)
    
    # Cache control
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    def is_expired(self) -> bool:
        """Check if vulnerability data is expired."""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f"<Vulnerability {self.cve_id}>"


# ===== DATABASE OPERATIONS =====

async def get_or_create_repository(
    session: AsyncSession,
    owner: str,
    repo: str,
    url: str,
) -> Repository:
    """Get existing repository or create new one."""
    from sqlalchemy import select
    
    stmt = select(Repository).where(
        (Repository.owner == owner) &
        (Repository.repo == repo)
    )
    result = await session.execute(stmt)
    repository = result.scalar_one_or_none()
    
    if not repository:
        repository = Repository(
            owner=owner,
            repo=repo,
            url=url,
        )
        session.add(repository)
        await session.commit()
    
    return repository


async def save_audit_result(
    session: AsyncSession,
    repository_id: str,
    audit_result,
) -> Audit:
    """Save audit result to database."""
    
    audit = Audit(
        audit_id=audit_result.audit_id,
        repository_id=repository_id,
        overall_score=audit_result.scores.overall,
        ip_legal_score=audit_result.scores.ip_legal,
        team_score=audit_result.scores.team_sustainability,
        code_quality_score=audit_result.scores.code_quality,
        security_score=audit_result.scores.security,
        status="COMPLETED",
        go_no_go=audit_result.go_no_go_recommendation,
        technical_debt_cost=audit_result.financial_impact.technical_debt_cost_usd,
        compliance_risk_cost=audit_result.financial_impact.compliance_risk_cost_usd,
        security_risk_cost=audit_result.financial_impact.security_risk_cost_usd,
        team_risk_cost=audit_result.financial_impact.team_risk_cost_usd,
        total_risk_usd=audit_result.financial_impact.total_risk_usd,
        valuation_discount_percent=audit_result.financial_impact.valuation_discount_percent,
        executive_summary=audit_result.executive_summary,
        red_flags=audit_result.red_flags,
        critical_findings_count=len(audit_result.critical_findings),
        completed_at=datetime.utcnow(),
        duration_seconds=audit_result.audit_duration_seconds,
    )
    
    # Add findings
    for finding in audit_result.findings:
        audit_finding = AuditFinding(
            category=finding.category,
            severity=finding.severity,
            title=finding.title,
            description=finding.description,
            recommendation=finding.recommendation,
            affected_items=finding.affected_items or [],
            estimation_hours=finding.estimation_hours or 0,
            evidence=finding.evidence,
            audit=audit,
        )
        session.add(audit_finding)
    
    session.add(audit)
    await session.commit()
    await session.refresh(audit)
    
    return audit
