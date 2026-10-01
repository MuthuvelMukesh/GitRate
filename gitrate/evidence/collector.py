"""Evidence collector: orchestrates all collectors into one auditable collection.

The collector is deliberately *offline*: it never calls a remote API, which is what
makes audits reproducible and testable.  Domains that would require external services
(vulnerability feeds, registry metadata, issues/PRs, cloud billing) are recorded as
unavailable in the completeness report instead of being skipped silently.

Risk score methodology (documented so it can be challenged):

* each finding contributes ``base_penalty[severity] * (0.5 + 0.5 * confidence)``
  - CRITICAL 25, HIGH 12, MEDIUM 5, LOW 1, INFO 0;
* ``overall_risk_score = clamp(100 - sum(penalties), 0, 100)``;
* human-rejected findings contribute **zero** penalty, human-validated findings keep
  their full weight - automated analysis and human conclusions are never mixed;
* the score is a relative indicator derived from *this* rule set
  (``ANALYSIS_VERSION``), not an absolute industry benchmark.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from gitrate import ANALYSIS_VERSION
from gitrate.evidence.completeness import (
    CompletenessReport,
    DataDomain,
    DomainAvailability,
    assess_completeness,
)
from gitrate.evidence.dependency_evidence import DependencyEvidence, collect_dependency_evidence
from gitrate.evidence.git_evidence import GitHistoryEvidence, collect_git_evidence
from gitrate.evidence.models import Finding, ReviewStatus, Severity, sort_findings
from gitrate.evidence.repository_evidence import RepositoryEvidence, collect_repository_evidence

# Penalty model: severity weight scaled by finding confidence (0.5..1.0).
BASE_PENALTY: dict[Severity, float] = {
    Severity.CRITICAL: 25.0,
    Severity.HIGH: 12.0,
    Severity.MEDIUM: 5.0,
    Severity.LOW: 1.0,
    Severity.INFO: 0.0,
}


@dataclass
class EvidenceCollection:
    """Everything an audit produced, with explicit completeness."""

    repository_slug: str
    repository: RepositoryEvidence
    git_history: Optional[GitHistoryEvidence]
    dependencies: DependencyEvidence
    completeness: CompletenessReport
    analysis_version: str = ANALYSIS_VERSION

    @property
    def findings(self) -> list[Finding]:
        """All findings across collectors, severity-sorted."""
        bundles: list[list[Finding]] = [self.repository.findings, self.dependencies.findings]
        if self.git_history is not None:
            bundles.append(self.git_history.findings)
        findings: list[Finding] = []
        for bundle in bundles:
            findings.extend(bundle)
        return sort_findings(findings)

    @property
    def evidence_count(self) -> int:
        """Total evidence items across collectors."""
        total = self.repository.evidence_count + self.dependencies.evidence_count
        if self.git_history is not None:
            total += self.git_history.evidence_count
        return total

    # -- scoring ------------------------------------------------------------------
    @staticmethod
    def _score(findings: list[Finding]) -> float:
        """Apply the documented penalty model to a set of findings."""
        penalty = sum(
            BASE_PENALTY[f.severity]
            * (0.5 + 0.5 * f.confidence)
            * (0.0 if f.review_status is ReviewStatus.HUMAN_REJECTED else 1.0)
            for f in findings
        )
        return round(max(0.0, min(100.0, 100.0 - penalty)), 2)

    @property
    def overall_risk_score(self) -> float:
        """Overall risk score 0-100 (higher = healthier)."""
        return self._score(self.findings)

    @property
    def category_scores(self) -> dict[str, float]:
        """Risk score per finding category (0-100, higher = healthier)."""
        grouped: dict[str, list[Finding]] = {}
        for finding in self.findings:
            grouped.setdefault(finding.category, []).append(finding)
        return {category: self._score(items) for category, items in sorted(grouped.items())}

    def to_dict(self) -> dict[str, object]:
        """Serialize for API/report output."""
        return {
            "repository": self.repository_slug,
            "analysis_version": self.analysis_version,
            "completeness": self.completeness.to_dict(),
            "evidence_count": self.evidence_count,
            "overall_risk_score": self.overall_risk_score,
            "category_scores": self.category_scores,
            "findings": [f.to_dict() for f in self.findings],
            "secrets_in_history": [
                s.to_dict() for s in (self.git_history.secrets if self.git_history else [])
            ],
        }

    def render(self) -> str:
        """Render the summary block used at the top of every report."""
        lines = [
            f"Overall Risk Score: {self.overall_risk_score:.0f}/100",
            f"Evidence Count: {self.evidence_count}",
            "",
            self.completeness.render(),
        ]
        return "\n".join(lines)


class EvidenceCollector:
    """Orchestrates all evidence collectors for one repository."""

    def __init__(
        self,
        *,
        max_commits: int = 5000,
        max_files: int = 20_000,
        scan_secrets: bool = True,
    ) -> None:
        """Configure collection budgets."""
        self.max_commits = max_commits
        self.max_files = max_files
        self.scan_secrets = scan_secrets

    def collect(
        self,
        repo_path: str | Path,
        *,
        repository_slug: Optional[str] = None,
    ) -> EvidenceCollection:
        """Collect evidence from a local repository checkout."""
        root = Path(repo_path).resolve()
        slug = repository_slug or root.name

        git_bundle: Optional[GitHistoryEvidence] = None
        git_detail = "no git history available"
        try:
            git_bundle = collect_git_evidence(
                root,
                max_commits=self.max_commits,
                scan_secrets=self.scan_secrets,
            )
            git_detail = (
                f"{git_bundle.stats.total_commits} commits analysed"
                + (" (truncated)" if git_bundle.stats.truncated else "")
            )
        except Exception as exc:  # GitCommandError and friends
            git_bundle = None
            git_detail = f"git history unavailable: {type(exc).__name__}: {exc}"

        repo_bundle = collect_repository_evidence(root, max_files=self.max_files)
        dep_bundle = collect_dependency_evidence(root)
        completeness = assess_completeness(self._domain_availability(repo_bundle, dep_bundle, git_bundle, git_detail))

        # Audit-level completeness is applied to every finding so that a thin-evidence
        # audit can never present confident conclusions.
        for finding in repo_bundle.findings + dep_bundle.findings:
            finding.data_completeness = completeness.completeness
        if git_bundle is not None:
            for finding in git_bundle.findings:
                finding.data_completeness = completeness.completeness

        return EvidenceCollection(
            repository_slug=slug,
            repository=repo_bundle,
            git_history=git_bundle,
            dependencies=dep_bundle,
            completeness=completeness,
        )

    @staticmethod
    def _domain_availability(
        repo_bundle: RepositoryEvidence,
        dep_bundle: DependencyEvidence,
        git_bundle: Optional[GitHistoryEvidence],
        git_detail: str,
    ) -> list[DomainAvailability]:
        """Report which evidence domains were actually available."""
        return [
            DomainAvailability(
                DataDomain.SOURCE_CODE,
                repo_bundle.files_scanned > 0,
                f"{repo_bundle.files_scanned} files scanned",
                repo_bundle.evidence_count,
            ),
            DomainAvailability(
                DataDomain.GIT_HISTORY,
                bool(git_bundle and git_bundle.stats.total_commits),
                git_detail,
                git_bundle.evidence_count if git_bundle else 0,
            ),
            DomainAvailability(
                DataDomain.DEPENDENCIES,
                bool(dep_bundle.manifests),
                (
                    f"{len(dep_bundle.manifests)} manifest(s), "
                    f"{len(dep_bundle.lock_files)} lock file(s)"
                ),
                dep_bundle.evidence_count,
            ),
            DomainAvailability(
                DataDomain.CI_CONFIGURATION,
                repo_bundle.has_ci,
                (
                    f"{len(repo_bundle.ci_files)} CI configuration file(s)"
                    if repo_bundle.has_ci
                    else "no CI configuration found"
                ),
                len(repo_bundle.ci_files),
            ),
            DomainAvailability(
                DataDomain.TESTS,
                repo_bundle.has_tests,
                (
                    f"{len(repo_bundle.test_files)} test file(s)"
                    if repo_bundle.has_tests
                    else "no test files found"
                ),
                len(repo_bundle.test_files),
            ),
            DomainAvailability(
                DataDomain.DOCUMENTATION,
                bool(repo_bundle.doc_files),
                (
                    f"{len(repo_bundle.doc_files)} documentation file(s)"
                    if repo_bundle.doc_files
                    else "no README/docs found"
                ),
                len(repo_bundle.doc_files),
            ),
            DomainAvailability(
                DataDomain.VULNERABILITY_FEEDS,
                False,
                "not queried: requires NVD/OSV access (not configured in offline mode)",
                0,
            ),
            DomainAvailability(
                DataDomain.PACKAGE_REGISTRY_METADATA,
                False,
                "not queried: registry freshness/maintainer data requires network access",
                0,
            ),
            DomainAvailability(DataDomain.ISSUES, False, "not fetched: issue tracker access not configured", 0),
            DomainAvailability(DataDomain.PULL_REQUESTS, False, "not fetched: PR data requires SCM API access", 0),
            DomainAvailability(
                DataDomain.ORGANIZATIONAL_EVIDENCE,
                False,
                "cannot be inferred from source code (access reviews, training, policies)",
                0,
            ),
            DomainAvailability(DataDomain.PRIVATE_INFRASTRUCTURE, False, "cannot be inferred from source code", 0),
            DomainAvailability(DataDomain.CLOUD_BILLING, False, "cannot be inferred from source code", 0),
            DomainAvailability(DataDomain.HR_RECORDS, False, "cannot be inferred from source code", 0),
        ]
        return domains

