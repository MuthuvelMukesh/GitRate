"""Supply-chain / dependency evidence.

Parses dependency manifests found in the working tree and turns them into structured
records plus evidence-backed findings.  Deterministic only:

* **no network access, no registry lookups** - freshness, CVE and maintainer-health
  claims require an external feed, so those domains are reported as *unavailable*
  rather than guessed (see :mod:`gitrate.evidence.completeness`);
* typosquatting and dependency-confusion are reported as *indicators* with the rule
  that fired, never as proof of malice.

Supported manifests: ``requirements*.txt``, ``pyproject.toml``, ``package.json``,
``go.mod``, ``Cargo.toml``.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from gitrate.evidence.models import (
    Evidence,
    EvidenceKind,
    EvidenceSource,
    Finding,
    Severity,
)

logger = logging.getLogger(__name__)

MANIFESTS: dict[str, str] = {
    "requirements.txt": "pypi",
    "requirements-dev.txt": "pypi",
    "pyproject.toml": "pypi",
    "package.json": "npm",
    "go.mod": "go",
    "Cargo.toml": "cargo",
}

# Well-known packages: a near-miss name is a typosquatting *indicator*.
WELL_KNOWN_PACKAGES: frozenset[str] = frozenset(
    {
        "requests", "flask", "django", "fastapi", "numpy", "pandas", "sqlalchemy", "pydantic",
        "celery", "redis", "boto3", "pytest", "urllib3", "cryptography", "aiohttp", "httpx",
        "gunicorn", "uvicorn", "click", "jinja2", "pyyaml", "setuptools", "wheel", "pip",
        "react", "react-dom", "vue", "express", "lodash", "axios", "webpack", "typescript",
    }
)

# Private-registry configuration is the usual dependency-confusion prerequisite.
PRIVATE_INDEX_PATTERN = re.compile(
    r"(?im)^\s*--index-url[=\s]+(\S+)"
    r"|\"(https?://[^\"\s]*(?:jfrog|artifactory|nexus|devpi|gemfury|myget|feed)[^\"\s]*)\""
)

# Lock files that make the *transitive* dependency set reproducible.
LOCK_FILES: tuple[str, ...] = (
    "requirements.lock",
    "poetry.lock",
    "Pipfile.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "go.sum",
    "Gemfile.lock",
)

_PINNED_PATTERN = re.compile(r"^(===|==)\s*\d")
_PY_REQUIREMENT = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._\-]*)\s*(?P<spec>[<>=!~^].*)?$")
_NPM_DEPENDENCY = re.compile(r"\"(?P<name>[@A-Za-z0-9][^\"\s]*)\"\s*:\s*\"(?P<spec>[^\"]+)\"")
_TOML_DEPENDENCY = re.compile(r"^(?P<name>[A-Za-z0-9._\-]+)\s*=\s*\"(?P<spec>[^\"]*)\"")
_GO_REQUIREMENT = re.compile(r"^\s*(?P<name>\S+)\s+(?P<spec>v\S+)")
_TOML_SECTION = re.compile(r"^\[(?P<section>[A-Za-z0-9.\-_]+)\]\s*$")
_FLOATING_NPM = ("*", "x", "latest")


@dataclass(frozen=True)
class Dependency:
    """One declared dependency."""

    name: str
    ecosystem: str
    version_spec: str = ""
    pinned: bool = False
    manifest: str = ""
    scope: str = "runtime"

    @property
    def normalized_name(self) -> str:
        """PEP 503 / npm-style normalisation used for comparisons."""
        return re.sub(r"[-_.]+", "-", self.name).lower().replace("@", "")


@dataclass
class DependencyEvidence:
    """Bundle of dependency evidence and findings."""

    dependencies: list[Dependency] = field(default_factory=list)
    manifests: list[str] = field(default_factory=list)
    lock_files: list[str] = field(default_factory=list)
    transitive_known: bool = False
    private_index_urls: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def evidence_count(self) -> int:
        """Total evidence items in this bundle."""
        return len(self.evidence) + sum(len(f.evidence) for f in self.findings)

    @property
    def unpinned(self) -> list[Dependency]:
        """Dependencies without an exact version pin."""
        return [d for d in self.dependencies if not d.pinned]

    @property
    def direct_count(self) -> int:
        """Number of directly declared dependencies."""
        return len(self.dependencies)



def _pypi_dependency(name: str, spec: str, manifest: str) -> Dependency:
    """Build a PyPI dependency record, normalising extras/markers out of the name."""
    return Dependency(
        name=name.split("[")[0].strip(),
        ecosystem="pypi",
        version_spec=spec.strip(),
        pinned=bool(_PINNED_PATTERN.match(spec)),
        manifest=manifest,
    )


def _cargo_dependency(name: str, spec: str, manifest: str) -> Dependency:
    """Build a Cargo dependency record (versions may be inline in the spec)."""
    version = spec
    if "{" in spec:
        version_match = re.search(r"version\s*=\s*\"([^\"]+)\"", spec)
        version = version_match.group(1) if version_match else ""
    return Dependency(
        name=name,
        ecosystem="cargo",
        version_spec=version,
        pinned=bool(_PINNED_PATTERN.match(version)),
        manifest=manifest,
    )


def _edit_distance_one_or_two(a: str, b: str) -> bool:
    """Cheap bounded Levenshtein check used for typosquatting indicators."""
    if a == b or abs(len(a) - len(b)) > 2:
        return False
    if len(a) == len(b):
        diff = sum(1 for x, y in zip(a, b) if x != y)
        return diff in (1, 2)
    shorter, longer = sorted((a, b), key=len)
    if len(longer) - len(shorter) == 1:
        for index in range(len(longer)):
            if longer[:index] + longer[index + 1 :] == shorter:
                return True
    return False


def parse_manifest(path: Path) -> list[Dependency]:
    """Parse one manifest file into :class:`Dependency` records."""
    ecosystem = MANIFESTS.get(path.name, "unknown")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:  # pragma: no cover - unreadable manifest
        return []
    dependencies: list[Dependency] = []
    section = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if path.name == "pyproject.toml":
            section_match = _TOML_SECTION.match(line)
            if section_match:
                section = section_match.group("section")
                continue
            if not section.endswith("dependencies"):
                continue
            match = _TOML_DEPENDENCY.match(line)
            if match:
                dependencies.append(
                    _pypi_dependency(match.group("name"), match.group("spec"), path.name)
                )
        elif path.name.startswith("requirements"):
            if line.startswith("-"):
                continue
            if " #" in line:
                line = line.split(" #", 1)[0].strip()
            match = _PY_REQUIREMENT.match(line)
            if match:
                dependencies.append(
                    _pypi_dependency(match.group("name"), match.group("spec") or "", path.name)
                )
        elif path.name == "package.json":
            match = _NPM_DEPENDENCY.search(line)
            if match:
                spec = match.group("spec")
                pinned = not any(token in spec for token in _FLOATING_NPM) and spec.startswith(
                    tuple("0123456789=~^v")
                )
                dependencies.append(
                    Dependency(
                        name=match.group("name"),
                        ecosystem=ecosystem,
                        version_spec=spec,
                        pinned=pinned,
                        manifest=path.name,
                        scope="dev" if "devDependencies" in raw_line else "runtime",
                    )
                )
        elif path.name == "go.mod":
            match = _GO_REQUIREMENT.match(line)
            if match and not line.startswith(("module ", "go ", "require", ")", "//")):
                dependencies.append(
                    Dependency(
                        name=match.group("name"),
                        ecosystem=ecosystem,
                        version_spec=match.group("spec"),
                        pinned=True,
                        manifest=path.name,
                    )
                )
        elif path.name == "Cargo.toml":
            match = _TOML_DEPENDENCY.match(line)
            if match:
                dependencies.append(
                    _cargo_dependency(match.group("name"), match.group("spec"), path.name)
                )
    return dependencies



def collect_dependency_evidence(
    root: str | Path,
    *,
    domain_completeness: float = 0.5,
) -> DependencyEvidence:
    """Collect dependency evidence for a repository working tree.

    Args:
        root: Repository root directory.
        domain_completeness: Completeness of the dependency domain.  Defaults to
            ``0.5`` because manifests are local but registry metadata, CVE feeds and
            transitive resolution need external services.

    Returns:
        A :class:`DependencyEvidence` bundle.
    """
    root_path = Path(root).resolve()
    bundle = DependencyEvidence()

    for name in MANIFESTS:
        for path in root_path.rglob(name):
            if ".git" in path.parts or "node_modules" in path.parts:
                continue
            bundle.manifests.append(path.relative_to(root_path).as_posix())
            bundle.dependencies.extend(parse_manifest(path))
    for name in LOCK_FILES:
        for path in root_path.rglob(name):
            if ".git" in path.parts or "node_modules" in path.parts:
                continue
            bundle.lock_files.append(path.relative_to(root_path).as_posix())
    bundle.transitive_known = bool(bundle.lock_files)

    for manifest_path in bundle.manifests:
        text = (root_path / manifest_path).read_text(encoding="utf-8", errors="replace")
        bundle.private_index_urls.extend(
            group for group in PRIVATE_INDEX_PATTERN.findall(text) if group
        )
    bundle.private_index_urls = sorted(set(bundle.private_index_urls))

    bundle.findings.extend(_dependency_findings_full(bundle, domain_completeness))
    for manifest in sorted(bundle.manifests)[:20]:
        count = len([d for d in bundle.dependencies if d.manifest == Path(manifest).name])
        bundle.evidence.append(
            Evidence(
                kind=EvidenceKind.DEPENDENCY,
                source=EvidenceSource.DEPENDENCIES,
                locator=manifest,
                detail=f"{count} declared dependencies in this manifest",
                metadata={"manifest": manifest},
            )
        )
    return bundle


def _dependency_findings(bundle: DependencyEvidence, completeness: float) -> list[Finding]:
    """Lockfile / pinning findings from manifest evidence."""
    findings: list[Finding] = []

    if bundle.dependencies and not bundle.transitive_known:
        finding = Finding(
            category="Supply Chain",
            severity=Severity.MEDIUM,
            title="No lockfile: transitive dependency versions are not reproducible",
            description=(
                f"{bundle.direct_count} direct dependencies are declared but no lock file was "
                "found. Builds are therefore not reproducible and the resolved transitive set "
                "cannot be audited."
            ),
            recommendation=(
                "Commit a lock file (requirements.lock / poetry.lock / package-lock.json / "
                "go.sum) and install from it in CI."
            ),
            confidence=0.85,
            data_completeness=completeness,
            rules_triggered=["dependencies.lockfile.missing"],
            impact="Non-reproducible builds; unauditable transitive dependency set.",
            estimated_effort_hours=4,
            tags=["supply_chain"],
            evidence=[
                Evidence(
                    kind=EvidenceKind.DEPENDENCY,
                    source=EvidenceSource.DEPENDENCIES,
                    locator="lockfiles",
                    detail="no lock file found next to the declared manifests",
                    metadata={
                        "manifests": sorted(bundle.manifests),
                        "checked_for": list(LOCK_FILES),
                    },
                )
            ],
        )
        findings.append(finding)

    unpinned = bundle.unpinned
    if unpinned:
        finding = Finding(
            category="Supply Chain",
            severity=Severity.MEDIUM,
            title=f"{len(unpinned)} dependencies are not pinned to exact versions",
            description=(
                "Floating version ranges mean a build can pick up a newly published release "
                "without review, which is a supply-chain risk vector."
            ),
            recommendation="Pin exact versions and update them deliberately through review.",
            confidence=0.9,
            data_completeness=completeness,
            rules_triggered=["dependencies.unpinned"],
            affected_components=sorted({d.name for d in unpinned})[:30],
            impact="Unreviewed dependency upgrades can introduce breaking or malicious changes.",
            estimated_effort_hours=8,
            tags=["supply_chain"],
            evidence=[
                Evidence(
                    kind=EvidenceKind.DEPENDENCY,
                    source=EvidenceSource.DEPENDENCIES,
                    locator=dependency.manifest,
                    detail=(
                        f"{dependency.name}{dependency.version_spec or ' (no specifier)'} in "
                        f"{dependency.manifest} is not pinned"
                    ),
                    metadata={
                        "name": dependency.name,
                        "spec": dependency.version_spec,
                        "ecosystem": dependency.ecosystem,
                    },
                )
                for dependency in unpinned[:20]
            ],
        )
        findings.append(finding)
    return findings


def _typosquatting_findings(bundle: DependencyEvidence, completeness: float) -> list[Finding]:
    """Indicators for near-miss package names (typosquatting)."""
    suspicious = [
        dependency
        for dependency in bundle.dependencies
        if dependency.normalized_name not in WELL_KNOWN_PACKAGES
        and any(
            _edit_distance_one_or_two(dependency.normalized_name, known)
            for known in WELL_KNOWN_PACKAGES
        )
    ]
    if not suspicious:
        return []
    finding = Finding(
        category="Supply Chain",
        severity=Severity.HIGH,
        title="Possible typosquatting indicator in dependencies",
        description=(
            "Dependencies whose names are one or two edits away from a well-known package were "
            "found. This is an indicator requiring human verification against the public "
            "registry, not proof of malice."
        ),
        recommendation=(
            "Verify each package's registry provenance (maintainer, publish history, repository "
            "URL) before accepting it into the build."
        ),
        confidence=0.55,
        data_completeness=completeness,
        rules_triggered=["dependencies.typosquatting_indicator"],
        affected_components=sorted({d.name for d in suspicious}),
        impact="Potential malicious package; requires registry verification.",
        estimated_effort_hours=2,
        tags=["supply_chain", "requires_human_review"],
        evidence=[
            Evidence(
                kind=EvidenceKind.DEPENDENCY,
                source=EvidenceSource.DEPENDENCIES,
                locator=dependency.manifest,
                detail=(
                    f"'{dependency.name}' is a near-miss of a well-known package name "
                    f"(declared in {dependency.manifest})"
                ),
                metadata={"name": dependency.name, "manifest": dependency.manifest},
            )
            for dependency in suspicious[:20]
        ],
    )
    return [finding]


def _private_index_findings(bundle: DependencyEvidence, completeness: float) -> list[Finding]:
    """Indicator for dependency-confusion exposure via private index configuration."""
    if not bundle.private_index_urls:
        return []
    finding = Finding(
        category="Supply Chain",
        severity=Severity.MEDIUM,
        title="Private package index configured (dependency-confusion exposure)",
        description=(
            "A private index/repository URL is configured in a manifest. If internal package "
            "names are not reserved on the public index, builds may resolve a public package "
            "instead of the internal one."
        ),
        recommendation=(
            "Reserve internal package names publicly and pin the index per-scope in the package "
            "manager configuration rather than in application manifests."
        ),
        confidence=0.6,
        data_completeness=completeness,
        rules_triggered=["dependencies.private_index"],
        affected_components=bundle.private_index_urls,
        impact="Dependency confusion can substitute attacker-controlled packages.",
        estimated_effort_hours=6,
        tags=["supply_chain", "requires_human_review"],
        evidence=[
            Evidence(
                kind=EvidenceKind.CONFIG,
                source=EvidenceSource.DEPENDENCIES,
                locator="manifests",
                detail=f"private index configuration found: {bundle.private_index_urls}",
                metadata={"indices": bundle.private_index_urls},
            )
        ],
    )
    return [finding]


def _missing_manifest_findings(bundle: DependencyEvidence, completeness: float) -> list[Finding]:
    """Finding when no manifest exists at all (explicit unknown, not a clean bill)."""
    if bundle.dependencies or bundle.manifests:
        return []
    finding = Finding(
        category="Supply Chain",
        severity=Severity.LOW,
        title="No dependency manifest detected",
        description=(
            "No dependency manifest was found, so third-party component risk could not be "
            "assessed. Absence of a manifest is not evidence of absence of dependencies."
        ),
        recommendation=(
            "Declare all third-party components in a manifest so the supply chain can be audited "
            "and an SBOM produced."
        ),
        confidence=0.7,
        data_completeness=completeness,
        rules_triggered=["dependencies.manifest.missing"],
        impact="Supply-chain risk cannot be evaluated.",
        estimated_effort_hours=4,
        tags=["supply_chain"],
        evidence=[
            Evidence(
                kind=EvidenceKind.DEPENDENCY,
                source=EvidenceSource.DEPENDENCIES,
                locator="manifests",
                detail="no supported manifest file found in the repository tree",
                metadata={"checked_for": sorted(MANIFESTS)},
            )
        ],
    )
    return [finding]


def _dependency_findings_full(bundle: DependencyEvidence, completeness: float) -> list[Finding]:
    """All dependency findings (used by :func:`collect_dependency_evidence`)."""
    return (
        _dependency_findings(bundle, completeness)
        + _typosquatting_findings(bundle, completeness)
        + _private_index_findings(bundle, completeness)
        + _missing_manifest_findings(bundle, completeness)
    )

