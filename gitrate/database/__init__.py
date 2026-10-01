"""Database package: ORM models, session management and migrations.

``models``        SQLAlchemy ORM models plus persistence helpers (legacy location kept).
``session``       Async engine/session factory, ``AsyncSessionLocal``, ``get_db`` dependency.
``tenancy``       Organization/User/Team/Repository tenancy models and isolation helpers.
``repositories``  Tenant-scoped query helpers used by the API layer.
"""

from gitrate.database.models import (
    Audit,
    AuditCache,
    AuditFinding,
    Base,
    GitHubMetrics,
    Repository,
    VulnerabilityCache,
    get_database_engine,
    get_or_create_repository,
    get_session_factory,
    init_db,
    save_audit_result,
)
from gitrate.database.session import AsyncSessionLocal, get_db

__all__ = [
    "Audit",
    "AuditCache",
    "AuditFinding",
    "AsyncSessionLocal",
    "Base",
    "GitHubMetrics",
    "Repository",
    "VulnerabilityCache",
    "get_database_engine",
    "get_db",
    "get_or_create_repository",
    "get_session_factory",
    "init_db",
    "save_audit_result",
]
