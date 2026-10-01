"""Evidence and finding models.

Design contract (see docs/ARCHITECTURE.md):

* An :class:`Evidence` records **one verifiable observation** - a file, a line, a
  commit, a dependency, a workflow, a rule that fired.  Evidence never contains raw
  credentials; secrets are represented by a keyed fingerprint.
* A :class:`Finding` is a conclusion.  It carries ``confidence``,
  ``data_completeness`` and at least one evidence item; constructing a finding of
  severity ``MEDIUM`` or above without evidence raises :class:`EvidenceRequiredError`.

This is what makes GitRate defensible: every conclusion can answer
*"why did GitRate reach this conclusion?"* by pointing at the observation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Optional

from gitrate.evidence.provenance import (
    ANALYSIS_VERSION,
    fingerprint,
    new_finding_id,
    utc_now,
)


class EvidenceRequiredError(ValueError):
    """Raised when a material finding is created without supporting evidence."""


class Severity(str, Enum):
    """Finding severity, ordered from least to most severe."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        """Numeric rank (bigger = more severe)."""
        return _SEVERITY_RANK[self]


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class EvidenceKind(str, Enum):
    """The kind of observation an evidence item represents."""

    FILE = "file"
    LINE = "line"
    COMMIT = "commit"
    GIT_REF = "git_ref"
    TAG = "tag"
    DEPENDENCY = "dependency"
    VULNERABILITY = "vulnerability"
    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
    WORKFLOW = "workflow"
    CONFIG = "configuration"
    RULE = "rule"
    MODEL = "model"
    METRIC = "metric"
    SECRET_FINGERPRINT = "secret_fingerprint"
    REVIEW = "review"


class EvidenceSource(str, Enum):
    """Which collector produced the evidence (i.e. which domain was available)."""

    REPOSITORY = "repository"
    GIT_HISTORY = "git_history"
    DEPENDENCIES = "dependencies"
    CI_CD = "ci_cd"
    DOCUMENTATION = "documentation"
    ISSUES = "issues"
    PULL_REQUESTS = "pull_requests"
    WORKFLOWS = "workflows"
    RELEASES = "releases"
    SECURITY = "security"
    EXTERNAL_API = "external_api"
    HUMAN_REVIEW = "human_review"


class ReviewStatus(str, Enum):
    """Human-in-the-loop state of a finding."""

    AUTOMATED = "AUTOMATED"
    HUMAN_VALIDATED = "HUMAN_VALIDATED"
    HUMAN_REJECTED = "HUMAN_REJECTED"


class ReviewAction(str, Enum):
    """Reviewer actions recorded in the immutable review trail."""

    CONFIRM = "CONFIRM"
    REJECT = "REJECT"
    MARK_FALSE_POSITIVE = "MARK_FALSE_POSITIVE"
    MODIFY_SEVERITY = "MODIFY_SEVERITY"
    ADD_EVIDENCE = "ADD_EVIDENCE"
    COMMENT = "COMMENT"


@dataclass(frozen=True)
class Evidence:
    """A single verifiable observation supporting a finding."""

    kind: EvidenceKind
    source: EvidenceSource
    locator: str
    detail: str
    observed_at: Optional[datetime] = None
    commit: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.locator:
            raise ValueError("Evidence.locator must not be empty")
        if not self.detail:
            raise ValueError("Evidence.detail must not be empty")

    @property
    def id(self) -> str:
        """Stable content-derived identifier (used for deduplication)."""


@dataclass
class Finding:
    """A conclusion backed by evidence, with explicit confidence and completeness."""

    category: str
    severity: Severity
    title: str
    description: str
    recommendation: str
    confidence: float
    data_completeness: float
    evidence: list[Evidence] = field(default_factory=list)
    rules_triggered: list[str] = field(default_factory=list)
    affected_components: list[str] = field(default_factory=list)
    impact: Optional[str] = None
    estimated_effort_hours: Optional[int] = None
    created_at: Optional[datetime] = None
    analysis_version: str = ANALYSIS_VERSION
    review_status: ReviewStatus = ReviewStatus.AUTOMATED
    finding_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if not 0.0 <= self.data_completeness <= 1.0:
            raise ValueError("data_completeness must be between 0.0 and 1.0")
        if self.severity.rank >= Severity.MEDIUM.rank and not self.evidence:
            raise EvidenceRequiredError(
                f"finding '{self.title}' has severity {self.severity.value} but no evidence; "
                "material findings must be traceable to at least one observation"
            )
        if self.finding_id is None:
            self.finding_id = new_finding_id(self.category, self.title)
        if self.created_at is None:
            self.created_at = utc_now()

    # -- evidence helpers ---------------------------------------------------------
    def add_evidence(self, item: Evidence) -> None:
        """Attach an evidence item (deduplicated by :attr:`Evidence.id`)."""
        if all(existing.id != item.id for existing in self.evidence):
            self.evidence.append(item)

    def extend_evidence(self, items: Iterable[Evidence]) -> None:
        """Attach several evidence items."""
        for item in items:
            self.add_evidence(item)

    @property
    def evidence_count(self) -> int:
        """Number of supporting observations."""
        return len(self.evidence)

    @property
    def source_files(self) -> list[str]:
        """Files referenced by the supporting evidence."""
        files = {
            str(item.metadata.get("file")) for item in self.evidence if item.metadata.get("file")
        }
        files.update(item.locator for item in self.evidence if item.kind is EvidenceKind.FILE)
        return sorted(files)

    @property
    def source_lines(self) -> list[int]:
        """Line numbers referenced by the supporting evidence."""
        return sorted(
            int(item.metadata["line"])
            for item in self.evidence
            if isinstance(item.metadata.get("line"), int)
        )

    # -- serialization ------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serialize to the canonical finding shape (see the upgrade specification)."""
        return {
            "finding_id": self.finding_id,
            "category": self.category,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "confidence": round(self.confidence, 4),
            "data_completeness": round(self.data_completeness, 4),
            "evidence": [item.to_dict() for item in self.evidence],
            "evidence_count": self.evidence_count,
            "source_files": self.source_files,
            "source_lines": self.source_lines,
            "commits": self.commits,
            "rules_triggered": list(self.rules_triggered),
            "affected_components": list(self.affected_components),
            "recommendation": self.recommendation,
            "impact": self.impact,
            "estimated_effort_hours": self.estimated_effort_hours,
            "review_status": self.review_status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "analysis_version": self.analysis_version,
            "tags": list(self.tags),
        }

    def to_json(self) -> str:
        """Serialize the finding to a JSON string."""
        return json.dumps(self.to_dict(), default=str, sort_keys=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Finding":
        """Rebuild a finding from :meth:`to_dict` output (e.g. persisted JSON)."""
        evidence = [
            Evidence(
                kind=EvidenceKind(item["kind"]),
                source=EvidenceSource(item["source"]),
                locator=item["locator"],
                detail=item["detail"],
                commit=item.get("commit"),
                metadata=item.get("metadata") or {},
            )
            for item in payload.get("evidence", [])
        ]
        return cls(
            category=payload["category"],
            severity=Severity(payload["severity"]),
            title=payload["title"],
            description=payload["description"],
            recommendation=payload["recommendation"],
            confidence=float(payload["confidence"]),
            data_completeness=float(payload["data_completeness"]),
            evidence=evidence,
            rules_triggered=list(payload.get("rules_triggered") or []),
            affected_components=list(payload.get("affected_components") or []),
            impact=payload.get("impact"),
            estimated_effort_hours=payload.get("estimated_effort_hours"),
            analysis_version=payload.get("analysis_version", ANALYSIS_VERSION),
            review_status=ReviewStatus(payload.get("review_status", "AUTOMATED")),
            finding_id=payload.get("finding_id"),
            tags=list(payload.get("tags") or []),
        )


def sort_findings(findings: Iterable[Finding]) -> list[Finding]:
    """Sort findings by severity (desc), then confidence (desc), then title."""
    return sorted(findings, key=lambda f: (-f.severity.rank, -f.confidence, f.title))


    @property
    def commits(self) -> list[str]:
        """Commit hashes referenced by the supporting evidence."""
        return sorted({item.commit for item in self.evidence if item.commit})

        return fingerprint(f"{self.kind.value}|{self.source.value}|{self.locator}|{self.detail}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the evidence JSON shape used by API responses and reports."""
        return {
            "evidence_id": self.id,
            "kind": self.kind.value,
            "source": self.source.value,
            "locator": self.locator,
            "detail": self.detail,
            "commit": self.commit,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "metadata": self.metadata,
        }
