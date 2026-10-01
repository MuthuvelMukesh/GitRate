"""GitRate - evidence-driven technical due-diligence intelligence platform.

Package layout
--------------
``gitrate.api``           FastAPI routers (HTTP surface, legacy dashboard routers)
``gitrate.auditors``      Domain auditors (security, code_quality, ip_legal, team, compliance)
``gitrate.core``          Audit orchestration, domain models, cache, task queue
``gitrate.database``      SQLAlchemy ORM, session management, Alembic migrations
``gitrate.evidence``      Evidence collection, provenance, completeness, evidence store
``gitrate.integrations``  External providers (GitHub API, multi-SCM abstraction)
``gitrate.intelligence``  Detectors, ML models, scoring profiles, confidence, recommendations
``gitrate.observability`` Prometheus metrics and alert helpers
``gitrate.reports``       Report generators (PDF, HTML, certificate, roadmap)
``gitrate.security``      Authentication, authorization, input validation, hardening
``gitrate.workers``       Celery application and asynchronous tasks

The canonical ASGI entrypoint is ``gitrate.main:app``.
"""

__version__ = "2.1.0"

# Analysis/rule version stamped onto every finding for reproducibility.
ANALYSIS_VERSION = "gitrate-2.1.0"

__all__ = ["__version__", "ANALYSIS_VERSION"]
