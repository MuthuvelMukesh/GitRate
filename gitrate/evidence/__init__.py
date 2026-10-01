"""Evidence engine: collection, provenance, completeness and storage.

Every conclusion GitRate produces must be traceable to evidence collected by one of
the collectors in this package.  See ``docs/ARCHITECTURE.md`` for the contract.
"""

from gitrate.evidence.collector import EvidenceCollection, EvidenceCollector
from gitrate.evidence.completeness import (
    CompletenessReport,
    DataDomain,
    DomainAvailability,
    assess_completeness,
)
from gitrate.evidence.evidence_store import EvidenceStore, InMemoryEvidenceStore, ReviewRecord
from gitrate.evidence.models import (
    Evidence,
    EvidenceKind,
    EvidenceRequiredError,
    EvidenceSource,
    Finding,
    ReviewAction,
    ReviewStatus,
    Severity,
    sort_findings,
)
from gitrate.evidence.provenance import (
    ANALYSIS_VERSION,
    fingerprint,
    new_finding_id,
    secret_fingerprint,
    utc_now,
)

__all__ = [
    "ANALYSIS_VERSION",
    "DataDomain",
    "DomainAvailability",
    "Evidence",
    "EvidenceCollector",
    "EvidenceCollection",
    "EvidenceKind",
    "EvidenceRequiredError",
    "EvidenceSource",
    "EvidenceStore",
    "Finding",
    "CompletenessReport",
    "InMemoryEvidenceStore",
    "ReviewAction",
    "ReviewRecord",
    "ReviewStatus",
    "Severity",
    "assess_completeness",
    "collect_repository_evidence",
    "fingerprint",
    "new_finding_id",
    "secret_fingerprint",
    "sort_findings",
    "utc_now",
]


def __getattr__(name: str):  # pragma: no cover - thin re-export convenience
    """Lazily re-export the heavier collectors to keep import cost low."""
    if name == "collect_repository_evidence":
        from gitrate.evidence.repository_evidence import collect_repository_evidence

        return collect_repository_evidence
    if name == "collect_git_evidence":
        from gitrate.evidence.git_evidence import collect_git_evidence

        return collect_git_evidence
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

