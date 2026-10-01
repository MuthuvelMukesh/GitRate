"""Compliance readiness audit domain.

Produces *readiness indicators* only - never certifications.  See
``gitrate/auditors/compliance/readiness_auditor.py`` and ``docs/LIMITATIONS.md``.
"""

from gitrate.auditors.compliance.readiness_auditor import ComplianceReadinessAuditor

__all__ = ["ComplianceReadinessAuditor"]
