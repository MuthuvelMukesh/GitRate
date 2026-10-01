"""Data completeness accounting.

An audit score is meaningless without knowing how much of the evidence surface was
actually available.  Two domains (source code + git history) can be inspected from a
local clone; issues, pull requests, releases and vulnerability feeds require external
APIs; HR records, cloud billing and private infrastructure are *not* inferable from a
repository at all.

This module makes that explicit: it records which domains were available, which were
not, and computes:

``coverage``      fraction of *considered* domains that yielded evidence
``completeness``  weighted fraction of the total evidence weight available

The confidence model in :mod:`gitrate.intelligence.confidence` consumes
``completeness`` and refuses to report high confidence on thin evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping


class DataDomain(str, Enum):
    """Evidence domains considered by an audit."""

    SOURCE_CODE = "source_code"
    GIT_HISTORY = "git_history"
    DEPENDENCIES = "dependencies"
    CI_CONFIGURATION = "ci_configuration"
    DOCUMENTATION = "documentation"
    TESTS = "tests"
    WORKFLOWS = "workflows"
    RELEASES = "releases"
    ISSUES = "issues"
    PULL_REQUESTS = "pull_requests"
    VULNERABILITY_FEEDS = "vulnerability_feeds"
    PACKAGE_REGISTRY_METADATA = "package_registry_metadata"
    ORGANIZATIONAL_EVIDENCE = "organizational_evidence"
    PRIVATE_INFRASTRUCTURE = "private_infrastructure"
    CLOUD_BILLING = "cloud_billing"
    HR_RECORDS = "hr_records"


# Weight rationale (documented so the number is falsifiable, not arbitrary):
#   * source_code / git_history are the primary evidence for technical due diligence
#     and are always available for a repository we are permitted to read -> 0.20 each.
#   * dependencies drive supply-chain risk -> 0.15
#   * ci_configuration / tests are strong quality+reliability signals -> 0.10 each
#   * documentation / releases / issues / pull_requests are supporting context -> 0.05 each
#   * vulnerability feeds and registry metadata materially strengthen dependency
#     findings but require network access -> 0.075 each
#   * organizational evidence cannot be inferred from source code; it keeps the
#     denominator honest so a repository-only audit can never score 100% completeness.
DOMAIN_WEIGHTS: Mapping[DataDomain, float] = {
    DataDomain.SOURCE_CODE: 0.20,
    DataDomain.GIT_HISTORY: 0.20,
    DataDomain.DEPENDENCIES: 0.15,
    DataDomain.CI_CONFIGURATION: 0.10,
    DataDomain.TESTS: 0.10,
    DataDomain.DOCUMENTATION: 0.05,
    DataDomain.RELEASES: 0.05,
    DataDomain.ISSUES: 0.05,
    DataDomain.PULL_REQUESTS: 0.05,
    DataDomain.VULNERABILITY_FEEDS: 0.075,
    DataDomain.PACKAGE_REGISTRY_METADATA: 0.075,
    DataDomain.ORGANIZATIONAL_EVIDENCE: 0.10,
}

# Domains that a repository-only audit can never satisfy; always reported as
# unavailable so that completeness cannot be overstated.
NOT_INFERABLE_FROM_SOURCE: frozenset[DataDomain] = frozenset(
    {
        DataDomain.ORGANIZATIONAL_EVIDENCE,
        DataDomain.PRIVATE_INFRASTRUCTURE,
        DataDomain.CLOUD_BILLING,
        DataDomain.HR_RECORDS,
    }
)


@dataclass(frozen=True)
class DomainAvailability:
    """Availability of a single evidence domain."""

    domain: DataDomain
    available: bool
    detail: str
    evidence_count: int = 0

    def to_dict(self) -> dict[str, object]:
        """Serialize for API/report output."""
        return {
            "domain": self.domain.value,
            "available": self.available,
            "detail": self.detail,
            "evidence_count": self.evidence_count,
        }


@dataclass
class CompletenessReport:
    """Result of :func:`assess_completeness`."""

    domains: list[DomainAvailability] = field(default_factory=list)
    completeness: float = 0.0
    coverage: float = 0.0
    evidence_count: int = 0

    @property
    def available_domains(self) -> list[DomainAvailability]:
        """Domains that yielded evidence."""
        return [d for d in self.domains if d.available]

    @property
    def unavailable_domains(self) -> list[DomainAvailability]:
        """Domains that were unavailable (and therefore limited the audit)."""
        return [d for d in self.domains if not d.available]

    def to_dict(self) -> dict[str, object]:
        """Serialize for API/report output."""
        return {
            "completeness": round(self.completeness, 4),
            "coverage": round(self.coverage, 4),
            "evidence_count": self.evidence_count,
            "available": [d.to_dict() for d in self.available_domains],
            "unavailable": [d.to_dict() for d in self.unavailable_domains],
        }

    def render(self) -> str:
        """Render the human-readable completeness block used in reports."""
        lines = [
            f"Data Completeness: {self.completeness * 100:.0f}%",
            f"Coverage: {self.coverage * 100:.0f}% of considered domains",
            "",
            "Available:",
        ]
        lines += [f"  [x] {d.domain.value}" for d in self.available_domains] or ["  (none)"]
        lines.append("Unavailable:")
        lines += [f"  [ ] {d.domain.value} - {d.detail}" for d in self.unavailable_domains]
        return "\n".join(lines)


def assess_completeness(
    domains: Iterable[DomainAvailability],
    *,
    weights: Mapping[DataDomain, float] | None = None,
) -> CompletenessReport:
    """Compute the weighted completeness of an audit's evidence surface.

    Args:
        domains: Availability status for each domain the audit attempted.
        weights: Optional override of :data:`DOMAIN_WEIGHTS`.

    Returns:
        A :class:`CompletenessReport` with ``completeness`` and ``coverage``.
    """
    weights = weights or DOMAIN_WEIGHTS
    statuses = list(domains)
    if not statuses:
        return CompletenessReport()

    considered_weight = sum(weights.get(d.domain, 0.0) for d in statuses)
    available_weight = sum(
        weights.get(d.domain, 0.0)
        for d in statuses
        if d.available and d.domain not in NOT_INFERABLE_FROM_SOURCE
    )
    completeness = available_weight / considered_weight if considered_weight else 0.0
    coverage = sum(1 for d in statuses if d.available) / len(statuses)

    return CompletenessReport(
        domains=statuses,
        completeness=round(min(1.0, max(0.0, completeness)), 4),
        coverage=round(coverage, 4),
        evidence_count=sum(d.evidence_count for d in statuses),
    )

