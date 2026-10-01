"""Git history forensics.

Collects evidence that cannot be seen in a snapshot of the working tree:

* contributor ownership and concentration
* code churn and abandoned modules
* large unexplained deletions and unusual commit bursts
* release/tag hygiene and branch activity
* historical secrets (present in history or deleted later)

Implementation notes
--------------------
* Uses the ``git`` CLI through :class:`GitRepository`, which passes an argument list
  (never a shell string) and enforces a timeout, so repository content cannot cause
  command injection.
* Works entirely offline against a local clone, which is what makes the end-to-end
  pipeline testable and reproducible without GitHub access.
* Historical secret scanning stores **fingerprints only** - raw credential values are
  never returned, logged or persisted.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from gitrate.evidence.models import (
    Evidence,
    EvidenceKind,
    EvidenceSource,
    Finding,
    Severity,
)
from gitrate.evidence.provenance import secret_fingerprint
from gitrate.evidence.redaction_profiles import PLACEHOLDER_VALUES as PLACEHOLDER_TOKENS
from gitrate.evidence.redaction_profiles import SECRET_PATTERNS

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 60
SECRET_SCAN_COMMIT_LIMIT = 500
BURST_WINDOW_HOURS = 6
BURST_COMMIT_THRESHOLD = 25
MASS_DELETION_LINES = 2000
MASS_DELETION_FILES = 15
ABANDONED_MODULE_DAYS = 365
OWNERSHIP_CONCENTRATION_HIGH = 0.70
OWNERSHIP_CONCENTRATION_MEDIUM = 0.50
INACTIVITY_DAYS_HIGH = 365
INACTIVITY_DAYS_MEDIUM = 180


class GitCommandError(RuntimeError):
    """Raised when a git command fails or times out."""


@dataclass(frozen=True)
class CommitRecord:
    """One commit with its diff statistics."""

    sha: str
    author: str
    email: str
    authored_at: datetime
    subject: str
    files_changed: int
    insertions: int
    deletions: int
    changed_paths: tuple[str, ...] = ()


@dataclass
class GitHistoryStats:
    """Aggregated history statistics for a repository."""

    commits: list[CommitRecord] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)
    current_branch: Optional[str] = None
    truncated: bool = False

    @property
    def total_commits(self) -> int:
        """Number of commits analysed."""
        return len(self.commits)

    @property
    def first_commit_at(self) -> Optional[datetime]:
        """Timestamp of the oldest analysed commit."""
        return self.commits[-1].authored_at if self.commits else None

    @property
    def last_commit_at(self) -> Optional[datetime]:
        """Timestamp of the newest analysed commit."""
        return self.commits[0].authored_at if self.commits else None

    @property
    def authors(self) -> Counter[str]:
        """Commit counts per author identity."""
        return Counter(c.author for c in self.commits)

    def commits_since(self, days: int, now: Optional[datetime] = None) -> list[CommitRecord]:
        """Return commits authored within the last ``days`` days."""
        now = now or datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        return [c for c in self.commits if c.authored_at >= cutoff]

    @property
    def ownership_concentration(self) -> float:
        """Share of commits authored by the single most prolific author (0..1)."""
        if not self.commits:
            return 0.0
        top = self.authors.most_common(1)[0][1]
        return top / len(self.commits)

    @property
    def inactive_days(self) -> Optional[int]:
        """Days since the last commit."""
        last = self.last_commit_at
        if last is None:
            return None
        return max(0, (datetime.now(timezone.utc) - last).days)

    def path_churn(self) -> dict[str, dict[str, int]]:
        """Per-path commit count, insertions and deletions."""
        churn: dict[str, dict[str, int]] = defaultdict(
            lambda: {"commits": 0, "insertions": 0, "deletions": 0}
        )
        for commit in self.commits:
            for path in commit.changed_paths:
                churn[path]["commits"] += 1
        return dict(churn)

    def last_commit_per_path(self) -> dict[str, datetime]:
        """Most recent commit timestamp per path (commits are newest-first)."""
        latest: dict[str, datetime] = {}
        for commit in self.commits:
            for path in commit.changed_paths:
                latest.setdefault(path, commit.authored_at)
        return latest



class GitRepository:
    """Safe, timeout-bounded wrapper around the ``git`` binary."""

    def __init__(self, path: str | Path, *, timeout: int = DEFAULT_TIMEOUT_SECONDS):
        self.path = Path(path).resolve()
        self.timeout = timeout
        if not (self.path / ".git").exists() and not (self.path / "HEAD").exists():
            raise GitCommandError(f"{self.path} is not a git repository")

    def run(self, *args: str) -> str:
        """Run a git command with an argument list (never a shell string)."""
        command = ["git", "-C", str(self.path), *args]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitCommandError(f"git {' '.join(args)} timed out after {self.timeout}s") from exc
        if result.returncode != 0:
            raise GitCommandError(
                f"git {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()[:500]}"
            )
        return result.stdout

    def is_repository(self) -> bool:
        """Return True when the path is a usable git repository."""
        try:
            self.run("rev-parse", "--is-inside-work-tree")
            return True
        except GitCommandError:
            return False

    def collect(self, *, max_commits: int = 5000) -> GitHistoryStats:
        """Collect commit history, tags and branches.

        Args:
            max_commits: Safety bound so very large histories stay inside the audit
                time budget; when hit, ``stats.truncated`` is set to True.
        """
        stats = GitHistoryStats()
        raw = self.run(
            "log",
            f"--max-count={max_commits + 1}",
            "--numstat",
            "--date=iso-strict",
            "--pretty=format:__C__%H%x1f%an%x1f%ae%x1f%ad%x1f%s",
        )
        commits = self._parse_log(raw)
        stats.truncated = len(commits) > max_commits
        stats.commits = commits[:max_commits]

        try:
            stats.tags = [t for t in self.run("tag", "--list").splitlines() if t.strip()]
        except GitCommandError:  # pragma: no cover - repositories without tags
            stats.tags = []
        try:
            stats.branches = [
                b.strip().lstrip("*").strip()
                for b in self.run("branch", "--list").splitlines()
                if b.strip()
            ]
        except GitCommandError:  # pragma: no cover
            stats.branches = []
        try:
            stats.current_branch = self.run("rev-parse", "--abbrev-ref", "HEAD").strip()
        except GitCommandError:  # pragma: no cover
            stats.current_branch = None
        return stats

    @staticmethod
    def _parse_log(raw: str) -> list[CommitRecord]:
        """Parse ``git log --numstat`` output into :class:`CommitRecord` objects."""
        commits: list[CommitRecord] = []
        current: Optional[dict] = None
        changed: list[str] = []
        files = insertions = deletions = 0

        def flush() -> None:
            if current is None:
                return
            commits.append(
                CommitRecord(
                    sha=current["sha"],
                    author=current["author"],
                    email=current["email"],
                    authored_at=current["date"],
                    subject=current["subject"],
                    files_changed=files,
                    insertions=insertions,
                    deletions=deletions,
                    changed_paths=tuple(changed),
                )
            )

        for line in raw.splitlines():
            if line.startswith("__C__"):
                flush()
                payload = line[len("__C__") :].split("\x1f")
                if len(payload) != 5:
                    current = None
                    continue
                sha, author, email, date_raw, subject = payload
                try:
                    authored_at = datetime.fromisoformat(date_raw)
                except ValueError:
                    authored_at = datetime.now(timezone.utc)
                if authored_at.tzinfo is None:
                    authored_at = authored_at.replace(tzinfo=timezone.utc)
                current = {
                    "sha": sha,
                    "author": author,
                    "email": email,
                    "date": authored_at,
                    "subject": subject,
                }
                changed, files, insertions, deletions = [], 0, 0, 0
                continue
            if not line.strip() or current is None:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, removed, path = parts
            changed.append(path)
            files += 1
            insertions += int(added) if added.isdigit() else 0
            deletions += int(removed) if removed.isdigit() else 0
        flush()
        return sorted(commits, key=lambda c: c.authored_at, reverse=True)


    def scan_history_for_secrets(
        self, *, max_commits: int = SECRET_SCAN_COMMIT_LIMIT
    ) -> list["HistoricalSecret"]:
        """Scan historical diffs for credential patterns.

        Returns fingerprints and locations only - never the credential value.
        """
        try:
            raw = self.run(
                "log",
                f"--max-count={max_commits}",
                "-p",
                "--all",
                "--no-color",
                "--unified=0",
                "--pretty=format:__C__%H",
            )
        except GitCommandError as exc:  # pragma: no cover - defensive
            logger.warning("Historical secret scan skipped: %s", exc)
            return []

        secrets: list[HistoricalSecret] = []
        sha, path, line_no = "unknown", "unknown", 0
        seen: set[str] = set()
        for line in raw.splitlines():
            if line.startswith("__C__"):
                sha = line[len("__C__") :].strip() or sha
                continue
            if line.startswith("+++ b/"):
                path = line[len("+++ b/") :].strip()
                continue
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                line_no = int(match.group(1)) if match else 0
                continue
            if not line.startswith("+") or line.startswith("+++"):
                continue
            for name, pattern in SECRET_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                value = match.group(1) if match.groups() else match.group(0)
                if any(token in value.lower() for token in PLACEHOLDER_TOKENS):
                    continue
                fp = secret_fingerprint(f"{name}:{value}")
                dedup = f"{name}:{fp}:{path}"
                if dedup in seen:
                    continue
                seen.add(dedup)
                secrets.append(
                    HistoricalSecret(
                        secret_type=name,
                        fingerprint=fp,
                        commit=sha,
                        file=path,
                        line=line_no,
                        status="present_in_history",
                    )
                )
        return secrets



@dataclass(frozen=True)
class HistoricalSecret:
    """A credential-like value observed in git history (fingerprint only)."""

    secret_type: str
    fingerprint: str
    commit: str
    file: str
    line: int
    status: str
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def to_dict(self) -> dict[str, object]:
        """Serialize without ever exposing the credential value."""
        return {
            "secret_type": self.secret_type,
            "fingerprint": self.fingerprint,
            "commit": self.commit,
            "file": self.file,
            "line": self.line,
            "status": self.status,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }

    def evidence(self) -> Evidence:
        """Evidence item describing where the credential-like value was found."""
        return Evidence(
            kind=EvidenceKind.SECRET_FINGERPRINT,
            source=EvidenceSource.GIT_HISTORY,
            locator=f"{self.file}:{self.line}@{self.commit[:12]}",
            detail=(
                f"{self.secret_type} pattern found in historical diff; "
                f"fingerprint={self.fingerprint} (value not stored or reported)"
            ),
            commit=self.commit,
            metadata={
                "file": self.file,
                "line": self.line,
                "secret_type": self.secret_type,
                "fingerprint": self.fingerprint,
            },
        )


REMEDIATION_GUIDANCE = [
    "Revoke the credential at the issuing provider.",
    "Rotate the credential and update the deployment secret store.",
    "Remove the credential from the current tree and add a scanner gate to CI.",
    "Rewrite history only if the repository's threat model requires it.",
    "Audit downstream usage/logs for the revoked credential.",
]


@dataclass
class GitHistoryEvidence:
    """Bundle of git-history evidence and deterministic findings."""

    stats: GitHistoryStats
    secrets: list[HistoricalSecret] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def evidence_count(self) -> int:
        """Number of collected evidence items (bundle-level plus finding-level)."""
        return len(self.evidence) + sum(len(f.evidence) for f in self.findings)


def _secret_findings(secrets: list[HistoricalSecret], completeness: float) -> list[Finding]:
    """Build one finding per distinct secret type observed in history."""
    by_type: dict[str, list[HistoricalSecret]] = defaultdict(list)
    for secret in secrets:
        by_type[secret.secret_type].append(secret)

    findings: list[Finding] = []
    for secret_type, items in sorted(by_type.items()):
        finding = Finding(
            category="Security",
            severity=Severity.CRITICAL,
            title=f"Credential-like value present in git history: {secret_type}",
            description=(
                f"{len(items)} historical occurrence(s) of a {secret_type} pattern were found in "
                "the commit history. Values are not stored; a salted fingerprint identifies each "
                "occurrence. Presence in history means the credential must be treated as "
                "compromised even if it was removed from the current tree."
            ),
            recommendation=" ".join(REMEDIATION_GUIDANCE),
            confidence=0.85 if secret_type != "password_literal" else 0.6,
            data_completeness=completeness,
            rules_triggered=[f"git_history.secret.{secret_type}"],
            affected_components=sorted({item.file for item in items}),
            impact="Potential credential exposure; requires human validation of whether it is live.",
            estimated_effort_hours=8,
            tags=["secret", "history", "requires_human_review"],
            evidence=[item.evidence() for item in items[:20]],
        )
        findings.append(finding)
    return findings



def _ownership_findings(stats: GitHistoryStats, completeness: float) -> list[Finding]:
    """Finding for contributor-concentration (bus-factor) risk."""
    if not stats.commits:
        return []
    authors = stats.authors
    top_author, top_commits = authors.most_common(1)[0]
    concentration = top_commits / stats.total_commits
    if concentration < OWNERSHIP_CONCENTRATION_MEDIUM:
        return []

    severity = Severity.HIGH if concentration >= OWNERSHIP_CONCENTRATION_HIGH else Severity.MEDIUM
    # Confidence scales with sample size: 30+ commits is a reasonable basis, fewer than
    # 10 commits is weak evidence and must not produce a confident finding.
    sample_confidence = min(1.0, stats.total_commits / 30.0)
    ownership_evidence: list[Evidence] = []
    for author, count in authors.most_common(5):
        lead_commit = next(c for c in stats.commits if c.author == author)
        ownership_evidence.append(
            Evidence(
                kind=EvidenceKind.COMMIT,
                source=EvidenceSource.GIT_HISTORY,
                locator=lead_commit.sha,
                detail=f"{author} authored {count} commit(s) in the analysed history",
                commit=lead_commit.sha,
                observed_at=lead_commit.authored_at,
                metadata={"author": author, "commits": count},
            )
        )
    finding = Finding(
        category="Team Sustainability",
        severity=severity,
        title="High contributor concentration (bus-factor risk)",
        description=(
            f"{top_author} authored {top_commits} of {stats.total_commits} commits "
            f"({concentration * 100:.0f}%). Knowledge is concentrated in a small number of "
            "contributors, which is a key-person risk indicator."
        ),
        recommendation=(
            "Introduce code ownership rotation, require review from a second engineer for "
            "critical paths, and document module-level onboarding material."
        ),
        confidence=round(0.55 + 0.4 * sample_confidence, 4),
        data_completeness=completeness,
        rules_triggered=["git_history.ownership.concentration"],
        affected_components=sorted(authors),
        impact="Key-person risk affecting delivery continuity after acquisition.",
        estimated_effort_hours=40,
        tags=["team", "bus_factor"],
        evidence=ownership_evidence,
    )
    return [finding]


def _inactivity_findings(stats: GitHistoryStats, completeness: float) -> list[Finding]:
    """Finding for a stale/abandoned repository."""
    inactive_days = stats.inactive_days
    if inactive_days is None or inactive_days < INACTIVITY_DAYS_MEDIUM:
        return []
    severity = Severity.HIGH if inactive_days > INACTIVITY_DAYS_HIGH else Severity.MEDIUM
    last = stats.last_commit_at
    assert last is not None  # guaranteed by inactive_days being not None
    finding = Finding(
        category="Team Sustainability",
        severity=severity,
        title="Repository shows sustained development inactivity",
        description=(
            f"No commits for {inactive_days} days (last commit {last.date().isoformat()}). "
            "Sustained inactivity is an indicator of reduced maintenance capacity."
        ),
        recommendation=(
            "Confirm the maintenance roadmap with the vendor, verify dependency currency, and "
            "budget for knowledge transfer before relying on this codebase."
        ),
        confidence=0.8,
        data_completeness=completeness,
        rules_triggered=["git_history.inactivity"],
        impact="Maintenance risk; security fixes may not be applied.",
        estimated_effort_hours=16,
        tags=["team", "maintenance"],
        evidence=[
            Evidence(
                kind=EvidenceKind.COMMIT,
                source=EvidenceSource.GIT_HISTORY,
                locator=stats.commits[0].sha,
                detail=f"last commit was {inactive_days} days before the audit",
                commit=stats.commits[0].sha,
                observed_at=last,
                metadata={"days_inactive": inactive_days},
            )
        ],
    )
    return [finding]



def _deletion_findings(stats: GitHistoryStats, completeness: float) -> list[Finding]:
    """Findings for large unexplained deletions and unusual commit bursts."""
    findings: list[Finding] = []

    for commit in stats.commits:
        if commit.deletions >= MASS_DELETION_LINES and commit.files_changed >= MASS_DELETION_FILES:
            finding = Finding(
                category="Code Quality",
                severity=Severity.MEDIUM,
                title="Large single-commit deletion requires explanation",
                description=(
                    f"Commit {commit.sha[:12]} removed {commit.deletions} lines across "
                    f"{commit.files_changed} files: \"{commit.subject}\"."
                ),
                recommendation=(
                    "Confirm with the maintainer whether the removed code moved elsewhere, was "
                    "obsolete, or represented functionality loss."
                ),
                confidence=0.6,
                data_completeness=completeness,
                rules_triggered=["git_history.mass_deletion"],
                affected_components=list(commit.changed_paths[:10]),
                impact="Potential functionality or test-coverage loss.",
                estimated_effort_hours=4,
                tags=["history", "requires_human_review"],
            )
            finding.add_evidence(
                Evidence(
                    kind=EvidenceKind.COMMIT,
                    source=EvidenceSource.GIT_HISTORY,
                    locator=commit.sha,
                    detail=(
                        f"deleted {commit.deletions} lines in {commit.files_changed} files "
                        f"(+{commit.insertions}/-{commit.deletions})"
                    ),
                    commit=commit.sha,
                    observed_at=commit.authored_at,
                    metadata={
                        "file": commit.changed_paths[0] if commit.changed_paths else "",
                        "deletions": commit.deletions,
                        "files_changed": commit.files_changed,
                    },
                )
            )
            findings.append(finding)

    windows: Counter[str] = Counter()
    window_repr: dict[str, CommitRecord] = {}
    for commit in stats.commits:
        key = commit.authored_at.strftime("%Y-%m-%dT%H")
        window_repr.setdefault(key, commit)
        windows[key] += 1
    for key, count in sorted(windows.items()):
        if count < BURST_COMMIT_THRESHOLD:
            continue
        sample = window_repr[key]
        finding = Finding(
            category="Code Quality",
            severity=Severity.LOW,
            title="Unusual commit burst detected",
            description=(
                f"{count} commits landed within the {key.replace('T', ' ')}:00 hour window. "
                "Bursts can indicate generated content, history rewriting, or an import of "
                "external code."
            ),
            recommendation="Verify the origin of burst commits before relying on history metrics.",
            confidence=0.5,
            data_completeness=completeness,
            rules_triggered=["git_history.commit_burst"],
            affected_components=[],
            impact="History metrics may be distorted; provenance of code needs review.",
            estimated_effort_hours=2,
            tags=["history", "requires_human_review"],
        )
        finding.add_evidence(
            Evidence(
                kind=EvidenceKind.METRIC,
                source=EvidenceSource.GIT_HISTORY,
                locator=f"burst:{key}",
                detail=f"{count} commits within one hour (threshold {BURST_COMMIT_THRESHOLD})",
                commit=sample.sha,
                observed_at=sample.authored_at,
                metadata={"commits": count, "window": key},
            )
        )
        findings.append(finding)
    return findings


def _module_findings(stats: GitHistoryStats, completeness: float) -> list[Finding]:
    """Finding for effectively abandoned modules (no commits for a long period)."""
    last_touch = stats.last_commit_per_path()
    churn = stats.path_churn()
    now = datetime.now(timezone.utc)
    abandoned = sorted(
        path
        for path, touched_at in last_touch.items()
        if (now - touched_at).days >= ABANDONED_MODULE_DAYS
        and churn.get(path, {}).get("commits", 0) >= 3
    )
    if not abandoned:
        return []
    finding = Finding(
        category="Code Quality",
        severity=Severity.MEDIUM,
        title="Modules effectively abandoned",
        description=(
            f"{len(abandoned)} file(s) have received no changes for more than "
            f"{ABANDONED_MODULE_DAYS} days after at least three commits. Abandoned modules often "
            "carry stale dependencies and undocumented assumptions."
        ),
        recommendation=(
            "Decide explicitly per module: retire it, or assign an owner and a migration plan."
        ),
        confidence=0.7,
        data_completeness=completeness,
        rules_triggered=["git_history.abandoned_module"],
        affected_components=abandoned[:20],
        impact="Maintenance cost and hidden dependency drift.",
        estimated_effort_hours=24,
        tags=["quality", "maintenance"],
    )
    for path in abandoned[:20]:
        touched_at = last_touch[path]
        finding.add_evidence(
            Evidence(
                kind=EvidenceKind.FILE,
                source=EvidenceSource.GIT_HISTORY,
                locator=path,
                detail=(
                    f"last modified {touched_at.date().isoformat()} "
                    f"({(now - touched_at).days} days ago)"
                ),
                observed_at=touched_at,
                metadata={"file": path, "days_since_change": (now - touched_at).days},
            )
        )
    return [finding]


def _release_hygiene_findings(stats: GitHistoryStats, completeness: float) -> list[Finding]:
    """Finding describing release/tag hygiene indicators."""
    if not stats.commits:
        return []
    tags = stats.tags
    semantic = [t for t in tags if re.match(r"^v?\d+\.\d+", t)]
    severity = Severity.LOW if semantic else Severity.MEDIUM
    finding = Finding(
        category="Compliance Readiness",
        severity=severity,
        title=(
            "Release tags follow semantic versioning"
            if semantic
            else "No semantic-version release tags found"
        ),
        description=(
            f"{len(tags)} tag(s) found, of which {len(semantic)} look like semantic versions. "
            "Release hygiene is a readiness indicator for traceable, auditable deployments; it is "
            "not evidence of a certification."
        ),
        recommendation=(
            "Adopt dated, immutable release tags with signed artifacts so that deployed revisions "
            "can be traced back to source."
        ),
        confidence=0.65,
        data_completeness=completeness,
        rules_triggered=["git_history.release_hygiene"],
        affected_components=[],
        impact="Weaker deployment traceability and auditability.",
        estimated_effort_hours=8,
        tags=["compliance_readiness", "release"],
    )
    if tags:
        finding.add_evidence(
            Evidence(
                kind=EvidenceKind.TAG,
                source=EvidenceSource.RELEASES,
                locator=tags[0],
                detail=f"{len(tags)} tag(s) present; {len(semantic)} semantic-version-like",
                metadata={"tags": tags[:20]},
            )
        )
    else:
        head = stats.commits[0]
        finding.add_evidence(
            Evidence(
                kind=EvidenceKind.GIT_REF,
                source=EvidenceSource.RELEASES,
                locator="refs/tags",
                detail="git tag --list returned no tags",
                commit=head.sha,
                observed_at=head.authored_at,
                metadata={"branch": stats.current_branch or "unknown"},
            )
        )
    return [finding]


def collect_git_evidence(
    repo_path: str | Path,
    *,
    max_commits: int = 5000,
    scan_secrets: bool = True,
    domain_completeness: float = 1.0,
) -> GitHistoryEvidence:
    """Collect all git-history evidence for a local repository.

    Args:
        repo_path: Path to a local git clone.
        max_commits: Upper bound on analysed commits (keeps audits inside budget).
        scan_secrets: Whether to scan historical diffs for credential patterns.
        domain_completeness: Completeness of the git-history domain (0..1).

    Returns:
        A :class:`GitHistoryEvidence` bundle with statistics, secrets and findings.
    """
    repository = GitRepository(repo_path)
    stats = repository.collect(max_commits=max_commits)
    secrets = repository.scan_history_for_secrets() if scan_secrets else []

    findings: list[Finding] = []
    findings += _secret_findings(secrets, domain_completeness)
    findings += _ownership_findings(stats, domain_completeness)
    findings += _inactivity_findings(stats, domain_completeness)
    findings += _module_findings(stats, domain_completeness)
    findings += _deletion_findings(stats, domain_completeness)
    findings += _release_hygiene_findings(stats, domain_completeness)

    bundle = GitHistoryEvidence(stats=stats, secrets=secrets, findings=findings)
    bundle.evidence.append(
        Evidence(
            kind=EvidenceKind.METRIC,
            source=EvidenceSource.GIT_HISTORY,
            locator=f"git:{Path(repo_path).name}",
            detail=(
                f"{stats.total_commits} commits, {len(stats.authors)} authors, "
                f"{len(stats.tags)} tags, {len(stats.branches)} branches"
                + (" (history truncated by audit budget)" if stats.truncated else "")
            ),
            commit=stats.commits[0].sha if stats.commits else None,
            observed_at=stats.last_commit_at,
            metadata={
                "total_commits": stats.total_commits,
                "authors": len(stats.authors),
                "tags": len(stats.tags),
                "branches": len(stats.branches),
                "truncated": stats.truncated,
            },
        )
    )
    return bundle

