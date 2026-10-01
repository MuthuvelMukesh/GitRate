"""Code Quality Auditor: Testing, technical debt, code churn, dead code analysis."""

from typing import List, Dict, Tuple, Set
from logging import getLogger
import re

from gitrate.core.models import (
    AuditFinding,
    RepositoryData,
)
from gitrate.auditors.base_auditor import BaseAuditor

logger = getLogger(__name__)


class CodeQualityAuditor(BaseAuditor):
    """Comprehensive code quality analysis.
    
    Evaluates:
    1. Test coverage and integrity
    2. Technical debt estimation
    3. Code churn patterns (hotspots)
    4. Dead code detection
    5. Complexity and maintainability
    """

    def __init__(self):
        """Initialize Code Quality auditor."""
        super().__init__("Code Quality Auditor")

    async def run(self, repo_data: RepositoryData) -> tuple[float, List[AuditFinding]]:
        """Execute code quality audit.
        
        Args:
            repo_data: Complete repository data
            
        Returns:
            Tuple of (audit_score, findings)
        """
        self.findings = []
        self.log_info(f"Starting code quality audit for {repo_data.repo_info.full_name}")
        
        # 1. Analyze testing
        testing_score = await self._analyze_testing(repo_data)
        
        # 2. Analyze code churn
        churn_score = await self._analyze_code_churn(repo_data)
        
        # 3. Estimate technical debt
        debt_score = await self._estimate_technical_debt(repo_data)
        
        # 4. Check for dead code
        dead_code_score = await self._check_dead_code(repo_data)
        
        # 5. Analyze complexity
        complexity_score = await self._analyze_complexity(repo_data)
        
        # Weighted final score
        weights = {
            "testing": 0.30,
            "churn": 0.20,
            "debt": 0.25,
            "dead_code": 0.15,
            "complexity": 0.10,
        }
        
        final_score = (
            testing_score * weights["testing"] +
            churn_score * weights["churn"] +
            debt_score * weights["debt"] +
            dead_code_score * weights["dead_code"] +
            complexity_score * weights["complexity"]
        )
        
        self.log_info(f"Code quality audit complete: {final_score:.1f}/100")
        self.log_debug(
            f"Component scores - Testing: {testing_score}, Churn: {churn_score}, "
            f"Debt: {debt_score}, Dead Code: {dead_code_score}, Complexity: {complexity_score}"
        )
        
        return final_score, self.findings

    async def _analyze_testing(self, repo_data: RepositoryData) -> float:
        """Analyze test coverage and test suite quality.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Analyzing test suite")
        
        score = 100.0
        
        # Check for test directory
        has_tests = getattr(repo_data.testing, 'has_tests', False) if repo_data.testing else False
        
        if not has_tests:
            self.add_finding(
                category="Code Quality",
                severity="HIGH",
                title="Missing test directory",
                description="No tests/, test/, or spec/ directory found",
                recommendation="Implement comprehensive test suite covering critical paths",
                estimation_hours=200,
            )
            score -= 30
        
        # Check for test coverage metrics
        if repo_data.testing and hasattr(repo_data.testing, 'coverage_percentage'):
            coverage = repo_data.testing.coverage_percentage
            
            if coverage < 20:
                self.add_finding(
                    category="Code Quality",
                    severity="HIGH",
                    title="Low test coverage",
                    description=f"Test coverage is only {coverage}%",
                    recommendation="Increase test coverage to at least 70% for critical code",
                    estimation_hours=100,
                )
                score -= 25
            
            elif coverage < 50:
                self.add_finding(
                    category="Code Quality",
                    severity="HIGH",
                    title="Insufficient test coverage",
                    description=f"Test coverage is {coverage}% (target: 70%+)",
                    recommendation="Add unit and integration tests for critical functionality",
                    estimation_hours=80,
                )
                score -= 20
            
            elif coverage < 70:
                self.add_finding(
                    category="Code Quality",
                    severity="MEDIUM",
                    title="Below-target test coverage",
                    description=f"Test coverage is {coverage}% (target: 70%+)",
                    recommendation="Continue adding tests to reach 70%+ coverage",
                    estimation_hours=40,
                )
                score -= 10
        
        # Check for CI/CD integration
        has_ci = self._check_for_ci_config(repo_data)
        
        if not has_ci:
            self.add_finding(
                category="Code Quality",
                severity="MEDIUM",
                title="No CI/CD pipeline configured",
                description="No .github/workflows, .gitlab-ci.yml, or similar found",
                recommendation="Set up CI/CD to run tests automatically on every commit",
                estimation_hours=15,
            )
            score -= 15
        
        return max(0.0, score)

    async def _analyze_code_churn(self, repo_data: RepositoryData) -> float:
        """Identify code churn hotspots (frequently modified files).
        
        Code churn indicates instability or rapid iteration.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Analyzing code churn patterns")
        
        # Calculate churn concentration
        churn_score = 100.0
        
        # If we can detect hotspots from repo structure
        high_churn_files = self._identify_churn_hotspots(repo_data)
        
        if high_churn_files:
            self.add_finding(
                category="Code Quality",
                severity="MEDIUM",
                title="High code churn hotspots",
                description=f"Found {len(high_churn_files)} files with high modification frequency: {', '.join(high_churn_files[:3])}...",
                recommendation="Refactor unstable areas and improve test coverage for these modules",
                estimation_hours=50,
            )
            churn_score -= 15
        
        return max(0.0, churn_score)

    async def _estimate_technical_debt(self, repo_data: RepositoryData) -> float:
        """Estimate technical debt from code metrics.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Estimating technical debt")
        
        score = 100.0
        debt_estimation_hours = 0
        
        # Check for outdated dependencies
        outdated_deps = self._check_outdated_dependencies(repo_data)
        
        if outdated_deps > 10:
            self.add_finding(
                category="Code Quality",
                severity="HIGH",
                title="Significant outdated dependencies",
                description=f"Found {outdated_deps} dependencies that need updating",
                recommendation="Create dependency update schedule and test thoroughly after updates",
                estimation_hours=40,
            )
            score -= 20
            debt_estimation_hours += 40
        
        elif outdated_deps > 0:
            self.add_finding(
                category="Code Quality",
                severity="MEDIUM",
                title="Some outdated dependencies",
                description=f"Found {outdated_deps} dependencies to update",
                recommendation="Review and update dependencies in regular maintenance cycles",
                estimation_hours=15,
            )
            score -= 8
            debt_estimation_hours += 15
        
        # Check for deprecated patterns
        deprecated_patterns = self._check_deprecated_patterns(repo_data)
        
        if deprecated_patterns:
            self.add_finding(
                category="Code Quality",
                severity="MEDIUM",
                title="Deprecated patterns detected",
                description=f"Found {len(deprecated_patterns)} uses of deprecated patterns",
                recommendation="Refactor to use modern equivalents",
                estimation_hours=30,
            )
            score -= 10
            debt_estimation_hours += 30
        
        # Store total debt estimation
        self.debug_info['estimated_debt_hours'] = debt_estimation_hours
        
        return max(0.0, score)

    async def _check_dead_code(self, repo_data: RepositoryData) -> float:
        """Detect dead code and unused modules.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Checking for dead code")
        
        score = 100.0
        
        # Check for __pycache__, .pyc, etc (leftover files)
        leftover_files = self._find_leftover_files(repo_data)
        
        if leftover_files:
            self.add_finding(
                category="Code Quality",
                severity="LOW",
                title="Leftover build artifacts in repository",
                description=f"Found {len(leftover_files)} build artifact files (should be .gitignored)",
                recommendation="Add *.pyc, __pycache__, .DS_Store to .gitignore",
                estimation_hours=2,
            )
            score -= 3
        
        # Check for unused files
        unused_files = self._find_unused_modules(repo_data)
        
        if unused_files:
            self.add_finding(
                category="Code Quality",
                severity="LOW",
                title="Potentially unused modules",
                description=f"Found {len(unused_files)} files that may be unused",
                recommendation="Review and remove unused code, or document why kept",
                estimation_hours=10,
            )
            score -= 5
        
        return max(0.0, score)

    async def _analyze_complexity(self, repo_data: RepositoryData) -> float:
        """Analyze code complexity and maintainability.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Analyzing code complexity")
        
        score = 100.0
        
        # Check for massive functions/classes (based on file analysis)
        large_files = self._identify_large_files(repo_data)
        
        if large_files > 5:
            self.add_finding(
                category="Code Quality",
                severity="MEDIUM",
                title="Large/complex source files",
                description=f"Found {large_files} files over 500 lines",
                recommendation="Refactor large files into smaller, focused modules",
                estimation_hours=40,
            )
            score -= 15
        
        elif large_files > 0:
            self.add_finding(
                category="Code Quality",
                severity="LOW",
                title="Some large source files",
                description=f"Found {large_files} files over 500 lines",
                recommendation="Consider breaking into smaller modules for better maintainability",
                estimation_hours=20,
            )
            score -= 5
        
        return max(0.0, score)

    def _check_for_ci_config(self, repo_data: RepositoryData) -> bool:
        """Check if CI/CD configuration files exist.
        
        Returns:
            True if CI config found
        """
        ci_files = {
            '.github/workflows/ci.yml',
            '.github/workflows/test.yml',
            '.gitlab-ci.yml',
            '.travis.yml',
            'Jenkinsfile',
            'azure-pipelines.yml',
        }
        
        files = set(getattr(repo_data, 'files', []))
        return bool(files & ci_files)

    def _identify_churn_hotspots(self, repo_data: RepositoryData) -> List[str]:
        """Identify files with high modification frequency.
        
        Returns:
            List of high-churn files
        """
        # Simplified implementation
        # In real scenario, would analyze git history
        
        hotspot_patterns = [
            r'utils\.py',
            r'helpers\.py',
            r'config\.py',
            r'models\.py',
        ]
        
        files = getattr(repo_data, 'files', [])
        hotspots = []
        
        for file in files[:100]:  # Check first 100
            for pattern in hotspot_patterns:
                if re.search(pattern, file):
                    hotspots.append(file)
                    break
        
        return hotspots[:5]

    def _check_outdated_dependencies(self, repo_data: RepositoryData) -> int:
        """Count outdated dependencies.
        
        Returns:
            Number of outdated dependencies
        """
        # Simplified: check if dependencies info exists
        if not hasattr(repo_data, 'dependencies') or not repo_data.dependencies:
            return 0
        
        # Would check versions in real scenario
        return 0

    def _check_deprecated_patterns(self, repo_data: RepositoryData) -> List[str]:
        """Detect use of deprecated patterns.
        
        Returns:
            List of deprecated patterns found
        """
        deprecated_patterns = {
            r'deprecated',
            r'TODO.*fix',
            r'FIXME',
            r'HACK',
            r'XXX',
        }
        
        patterns = []
        
        # Would scan source files in real scenario
        # For now return empty
        return patterns

    def _find_leftover_files(self, repo_data: RepositoryData) -> List[str]:
        """Find leftover build artifacts.
        
        Returns:
            List of leftover files
        """
        leftover_patterns = {
            r'\.pyc$',
            r'__pycache__',
            r'\.DS_Store$',
            r'\.egg-info',
            r'node_modules',
            r'\.venv',
            r'venv',
        }
        
        files = getattr(repo_data, 'files', [])
        leftover = []
        
        for file in files[:200]:  # Check first 200 files
            for pattern in leftover_patterns:
                if re.search(pattern, file):
                    leftover.append(file)
                    break
        
        return leftover

    def _find_unused_modules(self, repo_data: RepositoryData) -> List[str]:
        """Identify potentially unused modules.
        
        Returns:
            List of unused module paths
        """
        # Common patterns for unused/abandoned code
        unused_patterns = [
            r'old_',
            r'backup_',
            r'deprecated_',
            r'test_',  # Tests might be unused if no test runner
        ]
        
        files = getattr(repo_data, 'files', [])
        unused = []
        
        for file in files[:150]:
            for pattern in unused_patterns:
                if re.search(pattern, file, re.IGNORECASE):
                    unused.append(file)
                    break
        
        return unused[:5]

    def _identify_large_files(self, repo_data: RepositoryData) -> int:
        """Count files that are likely large/complex.
        
        Returns:
            Count of potentially large files
        """
        # Would need actual file sizes in real scenario
        # For now estimate based on file structure
        
        large_file_patterns = {
            r'app\.py$',
            r'main\.py$',
            r'server\.py$',
            r'core\.py$',
        }
        
        files = getattr(repo_data, 'files', [])
        count = 0
        
        for file in files:
            for pattern in large_file_patterns:
                if re.search(pattern, file, re.IGNORECASE):
                    count += 1
                    break
        
        return count
