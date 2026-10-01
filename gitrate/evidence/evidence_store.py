"""Evidence store: finding lifecycle, review actions and the immutable audit trail.

Two implementations are provided:

* :class:`InMemoryEvidenceStore` - process-local, used for API deployments without a
  database and by the test suite.
* Review records are **append-only**: a review action never mutates previous records,
  it only appends a new one and updates the finding's review status.  That is what
  makes the review trail auditable.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional, Protocol

from gitrate.evidence.models import (
    Evidence,
    Finding,
    ReviewAction,
    ReviewStatus,
    Severity,
    sort_findings,
)
from gitrate.evidence.provenance import utc_now


@dataclass(frozen=True)
class ReviewRecord:
    """One immutable human-review action."""

    review_id: str
    finding_id: str
    reviewer: str
    action: ReviewAction
    created_at: datetime
    comment: Optional[str] = None
    previous_severity: Optional[Severity] = None
    new_severity: Optional[Severity] = None
    added_evidence: tuple[Evidence, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Serialize for API/report output."""
        return {
            "review_id": self.review_id,
            "finding_id": self.finding_id,
            "reviewer": self.reviewer,
            "action": self.action.value,
            "created_at": self.created_at.isoformat(),
            "comment": self.comment,
            "previous_severity": self.previous_severity.value if self.previous_severity else None,
            "new_severity": self.new_severity.value if self.new_severity else None,
            "added_evidence": [item.to_dict() for item in self.added_evidence],
        }


class EvidenceStore(Protocol):
    """Storage contract for findings and review records."""

    def add_findings(self, findings: Iterable[Finding]) -> None:
        """Persist findings."""
        ...

    def get_finding(self, finding_id: str) -> Optional[Finding]:
        """Return a finding by identifier."""
        ...

    def list_findings(
        self,
        *,
        category: Optional[str] = None,
        severity: Optional[Severity] = None,
        review_status: Optional[ReviewStatus] = None,
    ) -> list[Finding]:
        """List findings filtered by the given criteria."""
        ...

    def record_review(
        self,
        finding_id: str,
        *,
        reviewer: str,
        action: ReviewAction,
        comment: Optional[str] = None,
        new_severity: Optional[Severity] = None,
        added_evidence: Optional[Iterable[Evidence]] = None,
    ) -> tuple[Finding, ReviewRecord]:
        """Append a review action and update the finding state."""
        ...

    def get_review_trail(self, finding_id: str) -> list[ReviewRecord]:
        """Return the immutable review trail of a finding."""
        ...


def _validate_action(
    action: ReviewAction,
    new_severity: Optional[Severity],
    added_evidence: Optional[Iterable[Evidence]],
) -> None:
    """Reject action/severity/evidence combinations that do not make sense."""
    if action is ReviewAction.MODIFY_SEVERITY and new_severity is None:
        raise ValueError("MODIFY_SEVERITY requires new_severity")
    if action is ReviewAction.ADD_EVIDENCE and not added_evidence:
        raise ValueError("ADD_EVIDENCE requires at least one evidence item")
    if action in (ReviewAction.CONFIRM, ReviewAction.REJECT, ReviewAction.MARK_FALSE_POSITIVE):
        if not comment:
            raise ValueError(f"{action.value} requires a justification comment")



class InMemoryEvidenceStore:
    """Thread-safe, process-local evidence store."""

    def __init__(self) -> None:
        self._findings: dict[str, Finding] = {}
        self._trail: dict[str, list[ReviewRecord]] = {}
        self._lock = threading.RLock()
        self._review_counter = 0

    # -- findings -----------------------------------------------------------------
    def add_findings(self, findings: Iterable[Finding]) -> None:
        """Persist (upsert) findings; existing identifiers are replaced."""
        with self._lock:
            for finding in findings:
                if finding.finding_id is None:  # pragma: no cover - defensive
                    continue
                self._findings[finding.finding_id] = finding

    def get_finding(self, finding_id: str) -> Optional[Finding]:
        """Return a finding by identifier."""
        with self._lock:
            return self._findings.get(finding_id)

    def list_findings(
        self,
        *,
        category: Optional[str] = None,
        severity: Optional[Severity] = None,
        review_status: Optional[ReviewStatus] = None,
    ) -> list[Finding]:
        """List findings filtered by the given criteria (severity-sorted)."""
        with self._lock:
            findings = list(self._findings.values())
        if category is not None:
            findings = [f for f in findings if f.category == category]
        if severity is not None:
            findings = [f for f in findings if f.severity is severity]
        if review_status is not None:
            findings = [f for f in findings if f.review_status is review_status]
        return sort_findings(findings)

    # -- human-in-the-loop review -------------------------------------------------
    def record_review(
        self,
        finding_id: str,
        *,
        reviewer: str,
        action: ReviewAction,
        comment: Optional[str] = None,
        new_severity: Optional[Severity] = None,
        added_evidence: Optional[Iterable[Evidence]] = None,
    ) -> tuple[Finding, ReviewRecord]:
        """Append a review action and update the finding's review status."""
        finding = self.get_finding(finding_id)
        if finding is None:
            raise KeyError(f"unknown finding: {finding_id}")
        evidence_items = list(added_evidence or [])
        _validate_action(action, new_severity, evidence_items)

        previous_severity = finding.severity
        with self._lock:
            self._review_counter += 1
            record = ReviewRecord(
                review_id=f"rev_{self._review_counter:06d}",
                finding_id=finding_id,
                reviewer=reviewer,
                action=action,
                created_at=utc_now(),
                comment=comment,
                previous_severity=previous_severity,
                new_severity=new_severity,
                added_evidence=tuple(evidence_items),
            )
            self._trail.setdefault(finding_id, []).append(record)

            if action is ReviewAction.CONFIRM:
                finding.review_status = ReviewStatus.HUMAN_VALIDATED
            elif action in (ReviewAction.REJECT, ReviewAction.MARK_FALSE_POSITIVE):
                finding.review_status = ReviewStatus.HUMAN_REJECTED
            elif action is ReviewAction.MODIFY_SEVERITY and new_severity is not None:
                finding.severity = new_severity
                finding.review_status = ReviewStatus.HUMAN_VALIDATED
            elif action is ReviewAction.ADD_EVIDENCE:
                finding.extend_evidence(evidence_items)
                finding.review_status = ReviewStatus.HUMAN_VALIDATED

        return finding, record

    def get_review_trail(self, finding_id: str) -> list[ReviewRecord]:
        """Return the immutable review trail of a finding."""
        with self._lock:
            return list(self._trail.get(finding_id, []))

    def stats(self) -> dict[str, int]:
        """Count findings per review status (used by dashboards and reports)."""
        with self._lock:
            findings = list(self._findings.values())
        return {
            "total": len(findings),
            "automated": sum(1 for f in findings if f.review_status is ReviewStatus.AUTOMATED),
            "human_validated": sum(
                1 for f in findings if f.review_status is ReviewStatus.HUMAN_VALIDATED
            ),
            "human_rejected": sum(
                1 for f in findings if f.review_status is ReviewStatus.HUMAN_REJECTED
            ),
            "review_actions": self._review_counter,
        }
