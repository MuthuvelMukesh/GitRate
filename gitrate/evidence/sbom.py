"""SBOM generation (SPDX 2.3 and CycloneDX 1.5).

Produces machine-readable software bills of materials from the dependency evidence
collected from manifests.  Honesty rules:

* only packages that were actually declared in a manifest are listed;
* the SBOM records the manifest they came from and whether a lock file made the
  transitive set reproducible;
* no hash/license/version data is invented - unknown fields are ``NOASSERTION``
  (SPDX) / omitted (CycloneDX) instead of fabricated.
"""

from __future__ import annotations

from typing import Any

from gitrate import ANALYSIS_VERSION
from gitrate.evidence.dependency_evidence import DependencyEvidence
from gitrate.evidence.provenance import utc_now


def generate_spdx_sbom(evidence: DependencyEvidence, *, repository: str) -> dict[str, Any]:
    """Generate an SPDX 2.3 JSON document."""
    now = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    packages: list[dict[str, Any]] = []
    for dependency in sorted(evidence.dependencies, key=lambda d: (d.ecosystem, d.name)):
        packages.append(
            {
                "name": dependency.name,
                "SPDXID": f"SPDXRef-Package-{dependency.normalized_name}",
                "versionInfo": dependency.version_spec or "NOASSERTION",
                "supplier": "NOASSERTION",
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": _purl(dependency),
                    }
                ],
                "comment": (
                    f"declared in {dependency.manifest} ({dependency.scope}); "
                    "version/license data requires registry lookup - NOASSERTION on purpose"
                ),
            }
        )

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": repository,
        "documentNamespace": f"https://gitrate.local/spdx/{repository}/{now}",
        "creationInfo": {
            "created": now,
            "creators": [f"Tool: GitRate-{ANALYSIS_VERSION}"],
            "licenseListVersion": "3.21",
            "comment": (
                "Generated from repository manifests. Transitive closure is only complete "
                f"when a lock file is present (present: {bool(evidence.lock_files)})."
            ),
        },
        "packages": packages,
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": "SPDXRef-RootPackage",
            }
        ],
    }


def generate_cyclonedx_sbom(evidence: DependencyEvidence, *, repository: str) -> dict[str, Any]:
    """Generate a CycloneDX 1.5 JSON document."""
    now = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
    components: list[dict[str, Any]] = []
    for dependency in sorted(evidence.dependencies, key=lambda d: (d.ecosystem, d.name)):
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": _purl(dependency),
            "name": dependency.name,
            "purl": _purl(dependency),
            "scope": "required" if dependency.scope == "runtime" else "optional",
        }
        if dependency.version_spec:
            component["version"] = dependency.version_spec.lstrip("^~><=! ")
        components.append(component)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:gitrate-{hash(repository) & 0xFFFFFFFF:08x}",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": {"components": [{"type": "application", "name": "GitRate", "version": ANALYSIS_VERSION}]},
            "component": {"type": "application", "name": repository, "bom-ref": "root"},
            "properties": [
                {
                    "name": "gitrate.dependency.lockfiles",
                    "value": ",".join(evidence.lock_files) or "none",
                },
                {
                    "name": "gitrate.sbom.scope",
                    "value": (
                        "direct dependencies from manifests; transitive closure requires a "
                        "lock file"
                    ),
                },
            ],
        },
        "components": components,
        "dependencies": [
            {"ref": "root", "dependsOn": [component["bom-ref"] for component in components]}
        ],
    }


def _purl(dependency) -> str:  # noqa: ANN001 - accepts Dependency only
    """Return the package URL for a dependency."""
    ecosystem = {
        "pypi": "pypi",
        "npm": "npm",
        "go": "golang",
        "cargo": "cargo",
        "maven": "maven",
        "rubygems": "gem",
    }.get(dependency.ecosystem, "generic")
    name = dependency.name
    version = dependency.version_spec.lstrip("^~><=! ") if dependency.version_spec else ""
    return f"pkg:{ecosystem}/{name}@{version}" if version else f"pkg:{ecosystem}/{name}"
