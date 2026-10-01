"""Repository (working-tree) evidence collection.

Collects what can be observed from the checked-out source tree:

* file inventory, languages and (approximate) lines of code
* test presence and test framework
* documentation presence (README, CONTRIBUTING, architecture docs)
* CI/CD configuration and containerisation
* licensing (LICENSE/COPYING + SPDX identifiers)
* risky constructs in source (``eval``, ``subprocess`` with ``shell=True``, ...)

Line counts are deliberately labelled as *approximate*: they are newline counts, not
statements, and the report states the method so nobody mistakes them for an exact
metric.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from gitrate.evidence.models import (
    Evidence,
    EvidenceKind,
    EvidenceSource,
    Finding,
    Severity,
)
from gitrate.evidence.redaction_profiles import BINARY_SUFFIXES, EXCLUDED_PATH_PARTS

logger = logging.getLogger(__name__)

LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".sql": "SQL",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".tf": "Terraform",
}

TEST_PATH_PATTERN = re.compile(r"(^|/)(tests?|spec|__tests__)(/|$)|(^|/)test_[^/]+\.py$|_test\.(go|py)$")
CI_PATH_PATTERN = re.compile(
    r"(^|/)\.github/workflows/[^/]+\.ya?ml$|(^|/)\.gitlab-ci\.yml$|(^|/)Jenkinsfile$"
    r"|(^|/)\.circleci/config\.yml$|(^|/)azure-pipelines\.yml$|(^|/)\.travis\.yml$"
)
DOC_PATHS = ("README.md", "README.rst", "README.txt", "README", "CONTRIBUTING.md", "docs/")
LICENSE_PATHS = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "LICENSE-APACHE", "LICENSE-MIT")
SPDX_ID_PATTERN = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+\-]+)")
LICENSE_KEYWORDS = {
    "MIT": re.compile(r"\bMIT License\b", re.IGNORECASE),
    "Apache-2.0": re.compile(r"Apache License,?\s+Version 2\.0", re.IGNORECASE),
    "GPL-3.0": re.compile(r"GNU GENERAL PUBLIC LICENSE\s+Version 3", re.IGNORECASE),
    "GPL-2.0": re.compile(r"GNU GENERAL PUBLIC LICENSE\s+Version 2", re.IGNORECASE),
    "AGPL-3.0": re.compile(r"GNU AFFERO GENERAL PUBLIC LICENSE", re.IGNORECASE),
    "BSD-3-Clause": re.compile(r"BSD 3-Clause", re.IGNORECASE),
    "BSD-2-Clause": re.compile(r"BSD 2-Clause", re.IGNORECASE),
    "MPL-2.0": re.compile(r"Mozilla Public License Version 2\.0", re.IGNORECASE),
    "ISC": re.compile(r"\bISC License\b", re.IGNORECASE),
    "Unlicense": re.compile(r"This is free and unencumbered software", re.IGNORECASE),
}

# Risky constructs are *indicators* for review, never proof of a vulnerability.
RISKY_PATTERNS: list[tuple[str, re.Pattern[str], Severity, str]] = [
    ("python.eval", re.compile(r"(?<![\w.])eval\s*\("), Severity.MEDIUM,
     "Use of eval() on dynamic input enables arbitrary code execution."),
    ("python.exec", re.compile(r"(?<![\w.])exec\s*\("), Severity.MEDIUM,
     "Use of exec() on dynamic input enables arbitrary code execution."),
    ("python.pickle_load", re.compile(r"pickle\.load[s]?\s*\("), Severity.MEDIUM,
     "Unpickling untrusted data allows arbitrary code execution."),
    ("python.shell_true", re.compile(r"subprocess\.[A-Za-z_]+\([^)]*shell\s*=\s*True"), Severity.HIGH,
     "shell=True on untrusted input enables command injection."),
    ("python.yaml_load", re.compile(r"yaml\.load\s*\((?![^)]*SafeLoader)"), Severity.MEDIUM,
     "yaml.load without SafeLoader can construct arbitrary Python objects."),
    ("python.verify_false", re.compile(r"verify\s*=\s*False"), Severity.HIGH,
     "TLS verification disabled enables machine-in-the-middle attacks."),
    ("js.inner_html", re.compile(r"dangerouslySetInnerHTML|\.innerHTML\s*="), Severity.MEDIUM,
     "Unescaped HTML injection can lead to cross-site scripting."),
]

MAX_FILE_BYTES = 400_000
LARGE_FILE_THRESHOLD_BYTES = 1_000_000


@dataclass
class RepositoryEvidence:
    """Evidence and findings derived from the working tree."""

    root: Path
    files_scanned: int = 0
    total_lines: int = 0
    lines_by_language: Counter = field(default_factory=Counter)
    test_files: list[str] = field(default_factory=list)
    ci_files: list[str] = field(default_factory=list)
    doc_files: list[str] = field(default_factory=list)
    license_files: list[str] = field(default_factory=list)
    detected_licenses: list[str] = field(default_factory=list)
    large_files: list[str] = field(default_factory=list)
    skipped_binary: int = 0
    findings: list[Finding] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def evidence_count(self) -> int:
        """Total evidence items in this bundle."""
        return len(self.evidence) + sum(len(f.evidence) for f in self.findings)

    @property
    def has_tests(self) -> bool:
        """Whether at least one test file was detected."""
        return bool(self.test_files)

    @property
    def has_ci(self) -> bool:
        """Whether at least one CI configuration was detected."""
        return bool(self.ci_files)

    @property
    def primary_language(self) -> Optional[str]:
        """Language with the most lines of code."""
        if not self.lines_by_language:
            return None
        return self.lines_by_language.most_common(1)[0][0]



def _is_excluded(relative: str) -> bool:
    """Return True when a path must be skipped (vendored/generated content)."""
    parts = set(Path(relative).parts)
    return bool(parts & EXCLUDED_PATH_PARTS)


def _iter_source_files(root: Path) -> Iterable[Path]:
    """Yield candidate source files, skipping vendored/binary content."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if _is_excluded(relative):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        yield path


def _detect_licenses(text: str) -> list[str]:
    """Detect SPDX identifiers or well-known license texts in a document."""
    if not text:
        return []
    found = set(SPDX_ID_PATTERN.findall(text))
    for spdx, pattern in LICENSE_KEYWORDS.items():
        if pattern.search(text):
            found.add(spdx)
    return sorted(found)


def collect_repository_evidence(
    root: str | Path,
    *,
    domain_completeness: float = 1.0,
    max_files: int = 20_000,
) -> RepositoryEvidence:
    """Collect working-tree evidence for a repository.

    Args:
        root: Repository root directory.
        domain_completeness: Completeness of the source-code domain (0..1).
        max_files: Safety bound on the number of files inspected.

    Returns:
        A :class:`RepositoryEvidence` bundle.
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError(f"{root_path} is not a directory")

    bundle = RepositoryEvidence(root=root_path)
    risky_hits: dict[str, list[tuple[str, int]]] = {}
    license_names = {name.upper() for name in LICENSE_PATHS}

    for path in _iter_source_files(root_path):
        if bundle.files_scanned >= max_files:
            logger.info("Repository scan truncated at %s files", max_files)
            break
        relative = path.relative_to(root_path).as_posix()
        try:
            size = path.stat().st_size
        except OSError:  # pragma: no cover - unreadable file
            continue
        if size > LARGE_FILE_THRESHOLD_BYTES:
            bundle.large_files.append(relative)
        bundle.files_scanned += 1

        suffix = path.suffix.lower()
        language = LANGUAGE_BY_SUFFIX.get(suffix)
        if language:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:  # pragma: no cover - unreadable file
                continue
            line_count = text.count("\n") + 1
            bundle.total_lines += line_count
            bundle.lines_by_language[language] += line_count
            if TEST_PATH_PATTERN.search(relative):
                bundle.test_files.append(relative)
            if size <= MAX_FILE_BYTES:
                for name, pattern, _severity, _why in RISKY_PATTERNS:
                    for match in pattern.finditer(text):
                        line_no = text.count("\n", 0, match.start()) + 1
                        risky_hits.setdefault(name, []).append((relative, line_no))
        elif suffix in {".md", ".rst", ".txt"}:
            if relative.startswith("docs/") or Path(relative).name.upper().startswith("README"):
                bundle.doc_files.append(relative)
        if CI_PATH_PATTERN.search("/" + relative) or Path(relative).name.startswith("Dockerfile"):
            bundle.ci_files.append(relative)
        if path.name.upper() in license_names:
            text = path.read_text(encoding="utf-8", errors="replace")[:20_000]
            bundle.license_files.append(relative)
            for spdx in _detect_licenses(text):
                if spdx not in bundle.detected_licenses:
                    bundle.detected_licenses.append(spdx)

    bundle.findings.extend(_build_findings(bundle, risky_hits, domain_completeness))
    bundle.evidence.append(
        Evidence(
            kind=EvidenceKind.METRIC,
            source=EvidenceSource.REPOSITORY,
            locator=f"tree:{root_path.name}",
            detail=(
                f"{bundle.files_scanned} files scanned, {bundle.total_lines} lines, "
                f"primary language {bundle.primary_language or 'unknown'}"
            ),
            metadata={
                "files_scanned": bundle.files_scanned,
                "total_lines": bundle.total_lines,
                "lines_by_language": dict(bundle.lines_by_language.most_common(10)),
                "large_files": bundle.large_files[:20],
            },
        )
    )
    return bundle



def _build_findings(
    bundle: RepositoryEvidence,
    risky_hits: dict[str, list[tuple[str, int]]],
    completeness: float,
) -> list[Finding]:
    """Turn observations into evidence-backed findings."""
    reasons: dict[str, str] = {name: why for name, _p, _s, why in RISKY_PATTERNS}
    severities: dict[str, Severity] = {name: sev for name, _p, sev, _w in RISKY_PATTERNS}
    findings: list[Finding] = []

    if not bundle.license_files:
        finding = Finding(
            category="IP & Legal",
            severity=Severity.HIGH,
            title="No license file detected",
            description=(
                "No LICENSE/COPYING file was found in the repository root. Without an explicit "
                "license the code is 'all rights reserved' by default, which is a distribution "
                "and reuse blocker for a potential acquirer. This is a potential licensing risk, "
                "not a legal conclusion."
            ),
            recommendation=(
                "Confirm the intended license with counsel and add an SPDX-tagged LICENSE file; "
                "audit third-party code for incompatible terms."
            ),
            confidence=0.9,
            data_completeness=completeness,
            rules_triggered=["repository.license.missing"],
            impact="Potential licensing risk (requires legal review).",
            estimated_effort_hours=8,
            tags=["license", "requires_human_review"],
            evidence=[
                Evidence(
                    kind=EvidenceKind.CONFIG,
                    source=EvidenceSource.REPOSITORY,
                    locator="LICENSE",
                    detail="no LICENSE/COPYING/LICENSE.md file present at repository root",
                    metadata={"checked": list(LICENSE_PATHS)},
                )
            ],
        )
        findings.append(finding)

    if not bundle.has_tests:
        finding = Finding(
            category="Code Quality",
            severity=Severity.HIGH,
            title="No automated tests detected",
            description=(
                "No test files or test directories were found. Without an automated test suite, "
                "change safety cannot be established, which raises regression risk for any "
                "post-acquisition work."
            ),
            recommendation=(
                "Establish a baseline test suite for the critical paths before modifying the "
                "codebase, and gate merges on it."
            ),
            confidence=0.85,
            data_completeness=completeness,
            rules_triggered=["repository.tests.missing"],
            impact="Regression risk; unknown functional contract.",
            estimated_effort_hours=80,
            tags=["quality", "testing"],
            evidence=[
                Evidence(
                    kind=EvidenceKind.METRIC,
                    source=EvidenceSource.REPOSITORY,
                    locator="tree:tests",
                    detail=(
                        f"{bundle.files_scanned} files scanned; no path matched a test convention "
                        "(tests/, spec/, test_*.py, *_test.go)"
                    ),
                    metadata={"files_scanned": bundle.files_scanned},
                )
            ],
        )
        findings.append(finding)

    if not bundle.has_ci:
        finding = Finding(
            category="Compliance Readiness",
            severity=Severity.MEDIUM,
            title="No CI/CD configuration detected",
            description=(
                "No pipeline configuration (GitHub Actions, GitLab CI, Jenkins, CircleCI) was "
                "found. This is a readiness gap for reproducible builds and change control, not "
                "evidence about certification."
            ),
            recommendation=(
                "Introduce a pipeline that runs tests, static analysis and dependency scanning on "
                "every change, with signed release artifacts."
            ),
            confidence=0.8,
            data_completeness=completeness,
            rules_triggered=["repository.ci.missing"],
            impact="Change control / auditability readiness gap.",
            estimated_effort_hours=16,
            tags=["compliance_readiness", "ci"],
            evidence=[
                Evidence(
                    kind=EvidenceKind.WORKFLOW,
                    source=EvidenceSource.CI_CD,
                    locator=".github/workflows",
                    detail="no recognised CI configuration file found in the repository tree",
                    metadata={
                        "expected": [".github/workflows/*.yml", ".gitlab-ci.yml", "Jenkinsfile"]
                    },
                )
            ],
        )
        findings.append(finding)

    findings.extend(_risky_construct_findings(risky_hits, completeness))
    return findings


def _risky_construct_findings(
    risky_hits: dict[str, list[tuple[str, int]]],
    completeness: float,
) -> list[Finding]:
    """Build findings for risky constructs found in source files."""
    reasons: dict[str, str] = {name: why for name, _p, _s, why in RISKY_PATTERNS}
    severities: dict[str, Severity] = {name: sev for name, _p, sev, _w in RISKY_PATTERNS}
    findings: list[Finding] = []
    for name, hits in sorted(risky_hits.items()):
        finding = Finding(
            category="Security",
            severity=severities[name],
            title=f"Risky construct detected: {name}",
            description=(
                f"{reasons[name]} Detected in {len(hits)} location(s). This is an indicator for "
                "review, not a confirmed vulnerability: exploitability depends on whether "
                "untrusted input reaches the call site."
            ),
            recommendation=(
                "Replace the construct with a safe alternative, or prove that untrusted input "
                "cannot reach it and record that justification next to the code."
            ),
            confidence=0.6,
            data_completeness=completeness,
            rules_triggered=[f"repository.risky.{name}"],
            affected_components=sorted({path for path, _line in hits}),
            impact="Potential injection / code-execution surface; requires human review.",
            estimated_effort_hours=4,
            tags=["security", "requires_human_review"],
            evidence=[
                Evidence(
                    kind=EvidenceKind.LINE,
                    source=EvidenceSource.REPOSITORY,
                    locator=f"{path}:{line_no}",
                    detail=f"{name} pattern matched at line {line_no}",
                    metadata={"file": path, "line": line_no},
                )
                for path, line_no in hits[:25]
            ],
        )
        findings.append(finding)
    return findings

