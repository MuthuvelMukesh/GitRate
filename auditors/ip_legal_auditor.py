"""IP & Legal Auditor: License, plagiarism, dependency provenance analysis."""

import re
from typing import List, Dict, Set, Tuple
from logging import getLogger
from collections import Counter

from core.models import (
    AuditFinding,
    RepositoryData,
)
from auditors.base_auditor import BaseAuditor

logger = getLogger(__name__)

# SPDX license categorization
PERMISSIVE_LICENSES = {
    "MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause",
    "ISC", "Unlicense", "MPL-2.0", "AGPL-3.0", "GPL-3.0"
}

COMMERCIAL_INCOMPATIBLE = {
    "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
    "GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0"
}

PROPRIETARY_COMPATIBLE = {
    "MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause",
    "ISC", "MPL-2.0", "Unlicense"
}

RISKY_LICENSES = {
    "AGPL-3.0", "GPL-3.0", "GPL-2.0",  # Copyleft
    "SSPL-1.0",  # Server Side Public License (controversial)
    "Business Source License 1.1",  # Non-open source
    "Proprietary",  # Closed source
}


class IPLegalAuditor(BaseAuditor):
    """Comprehensive IP & Legal audit for acquisition due diligence.
    
    Analyzes:
    1. Repository license (SPDX compliance)
    2. Dependency license compatibility
    3. Code plagiarism risk indicators
    4. License violation patterns
    5. Dependency provenance and security
    """

    def __init__(self):
        """Initialize IP & Legal auditor."""
        super().__init__("IP & Legal Auditor")

    async def run(self, repo_data: RepositoryData) -> tuple[float, List[AuditFinding]]:
        """Execute comprehensive IP & Legal audit.
        
        Args:
            repo_data: Complete repository data
            
        Returns:
            Tuple of (audit_score, findings)
        """
        self.findings = []
        self.log_info(f"Starting IP & Legal audit for {repo_data.name}")
        
        # 1. Analyze main repository license
        license_score = await self._audit_license(repo_data)
        
        # 2. Analyze dependencies for license compatibility
        dependency_score = await self._audit_dependencies(repo_data)
        
        # 3. Check for plagiarism risk indicators
        plagiarism_score = await self._check_plagiarism_risk(repo_data)
        
        # 4. Check for license violations
        violation_score = await self._check_license_violations(repo_data)
        
        # Calculate weighted score
        weights = {
            "license": 0.35,
            "dependencies": 0.30,
            "plagiarism": 0.20,
            "violations": 0.15,
        }
        
        final_score = (
            license_score * weights["license"] +
            dependency_score * weights["dependencies"] +
            plagiarism_score * weights["plagiarism"] +
            violation_score * weights["violations"]
        )
        
        self.log_info(f"IP & Legal audit complete: {final_score:.1f}/100")
        self.log_debug(
            f"Component scores - License: {license_score}, Dependencies: {dependency_score}, "
            f"Plagiarism: {plagiarism_score}, Violations: {violation_score}"
        )
        
        return final_score, self.findings

    async def _audit_license(self, repo_data: RepositoryData) -> float:
        """Analyze main repository license compliance.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Auditing repository license")
        
        license_name = repo_data.license or "UNKNOWN"
        score = 100.0
        
        # Check if license is identified
        if license_name == "UNKNOWN" or not license_name:
            self.add_finding(
                category="IP & Legal",
                severity="HIGH",
                title="Missing license",
                description="Repository has no SPDX license identifier specified",
                recommendation="Add LICENSE file with SPDX identifier (MIT, Apache-2.0, or GPL-3.0 recommended)",
                estimation_hours=2,
            )
            score -= 20
        
        # Check for commercial compatibility
        elif license_name in COMMERCIAL_INCOMPATIBLE:
            self.add_finding(
                category="IP & Legal",
                severity="HIGH",
                title=f"Copyleft license: {license_name}",
                description=f"License '{license_name}' requires source code disclosure in derivative works",
                recommendation="Consider dual-licensing or relicensing to MIT/Apache-2.0 if commercial use intended",
                estimation_hours=40,
            )
            score -= 15
        
        # Check for proprietary concerns
        elif license_name in RISKY_LICENSES:
            self.add_finding(
                category="IP & Legal",
                severity="MEDIUM",
                title=f"Potentially restrictive license: {license_name}",
                description=f"License '{license_name}' may have restrictions on use or modification",
                recommendation="Review license terms and consult legal team before acquisition",
                estimation_hours=5,
            )
            score -= 10
        
        self.log_debug(f"Repository license: {license_name}, score: {score}")
        return score

    async def _audit_dependencies(self, repo_data: RepositoryData) -> float:
        """Analyze dependency licenses for compatibility.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Auditing dependency licenses")
        
        # Extract dependencies from repo data
        dependencies = self._extract_dependencies(repo_data)
        
        if not dependencies:
            self.log_debug("No dependencies found to audit")
            return 100.0
        
        total_deps = len(dependencies)
        risk_score = 0.0
        
        # Categorize dependencies by risk
        high_risk_deps = []
        medium_risk_deps = []
        unknown_deps = []
        
        for dep in dependencies:
            if dep in RISKY_LICENSES:
                high_risk_deps.append(dep)
                risk_score += 5.0
            elif dep in COMMERCIAL_INCOMPATIBLE:
                medium_risk_deps.append(dep)
                risk_score += 2.0
            elif dep == "UNKNOWN":
                unknown_deps.append(dep)
                risk_score += 1.0
        
        score = max(0.0, 100.0 - risk_score)
        
        # Add findings for high-risk dependencies
        if high_risk_deps:
            self.add_finding(
                category="IP & Legal",
                severity="HIGH",
                title="High-risk dependency licenses detected",
                description=f"Found {len(high_risk_deps)} dependencies with copyleft/restrictive licenses: {', '.join(set(high_risk_deps))}",
                recommendation="Review these dependencies and consider alternatives with permissive licenses",
                estimation_hours=20,
            )
        
        if medium_risk_deps:
            self.add_finding(
                category="IP & Legal",
                severity="MEDIUM",
                title="Copyleft dependencies detected",
                description=f"Found {len(medium_risk_deps)} dependencies with copyleft licenses",
                recommendation="Ensure proper license compliance and consider license review",
                estimation_hours=10,
            )
        
        if unknown_deps:
            self.add_finding(
                category="IP & Legal",
                severity="MEDIUM",
                title="Unknown dependency licenses",
                description=f"Could not determine licenses for {len(unknown_deps)} dependencies",
                recommendation="Run dependency license scanner (license-checker, FOSSA, etc.)",
                estimation_hours=8,
            )
        
        self.log_debug(f"Dependency audit: {total_deps} total, {len(high_risk_deps)} high-risk, {len(medium_risk_deps)} medium-risk")
        return score

    async def _check_plagiarism_risk(self, repo_data: RepositoryData) -> float:
        """Check for plagiarism risk indicators.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Checking plagiarism risk indicators")
        
        score = 100.0
        
        # Check for very recent creation (could indicate copy)
        if repo_data.created_at:
            import datetime
            age_days = (datetime.datetime.now(datetime.timezone.utc) - repo_data.created_at).days
            
            if age_days < 7:
                self.add_finding(
                    category="IP & Legal",
                    severity="MEDIUM",
                    title="Very recent repository creation",
                    description=f"Repository created only {age_days} days ago",
                    recommendation="Verify origin of code and check for copied/forked content",
                    estimation_hours=10,
                )
                score -= 10
        
        # Check for unusual commit patterns (could indicate dumped code)
        if hasattr(repo_data, 'commits') and repo_data.commits:
            # If very few commits for size, might indicate dumped code
            if repo_data.commits.get('total_commits', 0) < 10:
                self.add_finding(
                    category="IP & Legal",
                    severity="MEDIUM",
                    title="Unusually low commit count",
                    description=f"Only {repo_data.commits.get('total_commits', 0)} commits found - may indicate code dump",
                    recommendation="Review commit history and code origin documentation",
                    estimation_hours=15,
                )
                score -= 8
        
        self.log_debug(f"Plagiarism risk score: {score}")
        return score

    async def _check_license_violations(self, repo_data: RepositoryData) -> float:
        """Check for license violation patterns.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Checking for license violations")
        
        score = 100.0
        
        # Check for missing attribution files (CONTRIBUTORS, CONTRIBUTORS.md)
        has_contrib_file = any(
            "contributor" in f.lower()
            for f in getattr(repo_data, 'files', [])
        )
        
        if not has_contrib_file and repo_data.contributors and repo_data.contributors.total_contributors > 5:
            self.add_finding(
                category="IP & Legal",
                severity="LOW",
                title="Missing CONTRIBUTORS file",
                description="Repository has multiple contributors but no CONTRIBUTORS file",
                recommendation="Add CONTRIBUTORS or CONTRIBUTORS.md to document contributions",
                estimation_hours=3,
            )
            score -= 3
        
        # Check for third-party code snippets without attribution
        # This is a simplified check based on file names
        potential_issues = self._check_attribution_patterns(repo_data)
        
        if potential_issues:
            self.add_finding(
                category="IP & Legal",
                severity="MEDIUM",
                title="Potential attribution gaps",
                description=f"Found {len(potential_issues)} files that may contain unattributed code",
                recommendation="Review these files for proper attribution of third-party code",
                estimation_hours=15,
            )
            score -= 5
        
        self.log_debug(f"License violation score: {score}")
        return score

    def _extract_dependencies(self, repo_data: RepositoryData) -> List[str]:
        """Extract dependency licenses from repository data.
        
        Returns:
            List of license identifiers
        """
        dependencies = []
        
        # Try to get from dependencies object
        if hasattr(repo_data, 'dependencies') and repo_data.dependencies:
            if hasattr(repo_data.dependencies, 'packages'):
                # If structured, extract licenses
                for pkg in repo_data.dependencies.packages[:10]:  # Sample first 10
                    if hasattr(pkg, 'license'):
                        dependencies.append(pkg.license)
        
        # Fallback: return empty or default
        if not dependencies:
            self.log_debug("No structured dependencies found")
        
        return dependencies

    def _check_attribution_patterns(self, repo_data: RepositoryData) -> List[str]:
        """Check for files that might contain unattributed code.
        
        Returns:
            List of suspicious files
        """
        suspicious_patterns = [
            r"third.?party",
            r"vendor",
            r"external",
            r"contrib",
        ]
        
        suspicious_files = []
        
        for file in getattr(repo_data, 'files', [])[:50]:  # Check first 50 files
            for pattern in suspicious_patterns:
                if re.search(pattern, file, re.IGNORECASE):
                    if "license" not in file.lower() and "attribution" not in file.lower():
                        suspicious_files.append(file)
                    break
        
        return list(set(suspicious_files))  # Deduplicate
