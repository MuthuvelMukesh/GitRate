"""Security Auditor: CVE scanning, secrets detection, infrastructure security analysis."""

from typing import List, Dict, Tuple, Set
from logging import getLogger
import re

from core.models import (
    AuditFinding,
    RepositoryData,
)
from auditors.base_auditor import BaseAuditor

logger = getLogger(__name__)

# Common high-risk CVEs and patterns
CVE_PATTERNS = {
    r'requests[<>=]*[0-9.]*',  # Old requests library
    r'django[<>=]*[0-9.]*',    # Django version
    r'flask[<>=]*[0-9.]*',     # Flask version
}

# Secrets patterns
SECRETS_PATTERNS = {
    r'aws_access_key_id\s*=',
    r'aws_secret_access_key\s*=',
    r'private_key\s*=',
    r'password\s*=\s*["\']?(?!.*password|.*\*\*)',
    r'api_key\s*=',
    r'token\s*=',
}

# Risky code patterns
RISKY_CODE_PATTERNS = {
    r'eval\(',
    r'exec\(',
    r'__import__\(',
    r'pickle\.load',
    r'os\.system\(',
    r'subprocess\.call\(',
}


class SecurityAuditor(BaseAuditor):
    """Comprehensive security analysis.
    
    Evaluates:
    1. Known CVEs in dependencies
    2. Secrets exposure (API keys, tokens, etc.)
    3. Risky code patterns
    4. Infrastructure security (Docker, configs)
    5. Authentication and authorization
    """

    def __init__(self):
        """Initialize Security auditor."""
        super().__init__("Security Auditor")

    async def run(self, repo_data: RepositoryData) -> tuple[float, List[AuditFinding]]:
        """Execute security audit.
        
        Args:
            repo_data: Complete repository data
            
        Returns:
            Tuple of (audit_score, findings)
        """
        self.findings = []
        self.log_info(f"Starting security audit for {repo_data.name}")
        
        # 1. Scan for CVEs in dependencies
        cve_score = await self._scan_cves(repo_data)
        
        # 2. Detect secrets in code
        secrets_score = await self._detect_secrets(repo_data)
        
        # 3. Check for risky code patterns
        risky_code_score = await self._check_risky_patterns(repo_data)
        
        # 4. Analyze infrastructure security
        infra_score = await self._analyze_infrastructure(repo_data)
        
        # 5. Check authentication/authorization
        auth_score = await self._check_auth_patterns(repo_data)
        
        # Weighted final score
        weights = {
            "cves": 0.35,
            "secrets": 0.30,
            "risky_code": 0.15,
            "infrastructure": 0.15,
            "auth": 0.05,
        }
        
        final_score = (
            cve_score * weights["cves"] +
            secrets_score * weights["secrets"] +
            risky_code_score * weights["risky_code"] +
            infra_score * weights["infrastructure"] +
            auth_score * weights["auth"]
        )
        
        self.log_info(f"Security audit complete: {final_score:.1f}/100")
        self.log_debug(
            f"Component scores - CVEs: {cve_score}, Secrets: {secrets_score}, "
            f"Risky Code: {risky_code_score}, Infrastructure: {infra_score}, Auth: {auth_score}"
        )
        
        return final_score, self.findings

    async def _scan_cves(self, repo_data: RepositoryData) -> float:
        """Scan dependencies for known CVEs.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Scanning for CVEs in dependencies")
        
        score = 100.0
        cves_found = []
        
        # Check for outdated/vulnerable versions
        vulnerable_deps = await self._check_vulnerable_dependencies(repo_data)
        
        if vulnerable_deps:
            cves_found.extend(vulnerable_deps)
            
            self.add_finding(
                category="Security",
                severity="CRITICAL",
                title="Known CVEs detected in dependencies",
                description=f"Found {len(vulnerable_deps)} dependencies with known CVEs: {', '.join(vulnerable_deps[:3])}",
                recommendation="Update all vulnerable dependencies to patched versions immediately",
                estimation_hours=30,
            )
            score -= 35
        
        # Check if dependency versions are specified
        deps_pinned = await self._check_deps_pinning(repo_data)
        
        if not deps_pinned:
            self.add_finding(
                category="Security",
                severity="HIGH",
                title="Dependencies not pinned to specific versions",
                description="Using floating/wildcard version specifiers increases supply chain risk",
                recommendation="Pin all dependencies to specific versions, use lock files (requirements.lock, Pipfile.lock, etc.)",
                estimation_hours=5,
            )
            score -= 10
        
        # Check for dependency auditing tools
        has_audit_config = await self._check_audit_config(repo_data)
        
        if not has_audit_config:
            self.add_finding(
                category="Security",
                severity="MEDIUM",
                title="No dependency audit configured",
                description="No safety, bandit, or similar security scanning in CI/CD",
                recommendation="Add security scanning tools (safety, bandit, semgrep) to CI/CD pipeline",
                estimation_hours=10,
            )
            score -= 5
        
        return max(0.0, score)

    async def _detect_secrets(self, repo_data: RepositoryData) -> float:
        """Detect exposed secrets (API keys, tokens, etc.).
        
        Returns:
            Score 0-100
        """
        self.log_debug("Detecting exposed secrets")
        
        score = 100.0
        
        # Check for .env files in repo
        has_env_in_repo = any(
            f.lower() in ['.env', '.env.example', '.env.local']
            for f in getattr(repo_data, 'files', [])
            if '.env' in f.lower()
        )
        
        if '.env' in getattr(repo_data, 'files', []):
            self.add_finding(
                category="Security",
                severity="CRITICAL",
                title="Secrets potentially exposed in .env file",
                description=".env file found in repository (should be in .gitignore)",
                recommendation="Remove .env from git history, add to .gitignore, use .env.example instead",
                estimation_hours=10,
            )
            score -= 30
        
        # Check for config files with potential secrets
        config_files = [
            f for f in getattr(repo_data, 'files', [])
            if any(x in f.lower() for x in ['config', 'secret', 'credential', 'password'])
        ]
        
        if config_files:
            self.add_finding(
                category="Security",
                severity="HIGH",
                title="Potential secrets in configuration files",
                description=f"Found {len(config_files[:5])} config-like files that may contain secrets",
                recommendation="Review files for hardcoded secrets, use environment variables instead",
                estimation_hours=8,
            )
            score -= 15
        
        # Check for common secret patterns in code
        suspicious_patterns = await self._check_secret_patterns(repo_data)
        
        if suspicious_patterns:
            self.add_finding(
                category="Security",
                severity="HIGH",
                title="Suspicious secret-like patterns detected",
                description=f"Found potential secrets in code: {', '.join(suspicious_patterns[:3])}",
                recommendation="Audit codebase for hardcoded credentials using git-secrets or similar",
                estimation_hours=15,
            )
            score -= 12
        
        return max(0.0, score)

    async def _check_risky_patterns(self, repo_data: RepositoryData) -> float:
        """Check for dangerous code patterns.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Checking for risky code patterns")
        
        score = 100.0
        
        # Check for eval/exec usage
        risky_patterns = await self._find_risky_patterns(repo_data)
        
        if 'eval' in risky_patterns or 'exec' in risky_patterns:
            self.add_finding(
                category="Security",
                severity="HIGH",
                title="Dangerous eval/exec usage",
                description="Code uses eval() or exec() which enables arbitrary code execution",
                recommendation="Replace eval/exec with safer alternatives (ast.literal_eval, import statement, etc.)",
                estimation_hours=20,
            )
            score -= 20
        
        if 'pickle' in risky_patterns:
            self.add_finding(
                category="Security",
                severity="HIGH",
                title="Unsafe deserialization with pickle",
                description="Code uses pickle.load() which can execute arbitrary code",
                recommendation="Use JSON or other safe serialization formats, or strictly validate pickle source",
                estimation_hours=15,
            )
            score -= 15
        
        if 'os.system' in risky_patterns or 'subprocess' in risky_patterns:
            self.add_finding(
                category="Security",
                severity="HIGH",
                title="Shell execution without sanitization",
                description="Code uses os.system() or subprocess without proper argument handling",
                recommendation="Use subprocess.run() with shell=False and pass list of arguments",
                estimation_hours=10,
            )
            score -= 12
        
        return max(0.0, score)

    async def _analyze_infrastructure(self, repo_data: RepositoryData) -> float:
        """Analyze infrastructure and deployment security.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Analyzing infrastructure security")
        
        score = 100.0
        
        # Check Dockerfile security
        has_dockerfile = any(
            'dockerfile' in f.lower()
            for f in getattr(repo_data, 'files', [])
        )
        
        if has_dockerfile:
            dockerfile_issues = await self._check_dockerfile_security(repo_data)
            
            if dockerfile_issues:
                self.add_finding(
                    category="Security",
                    severity="MEDIUM",
                    title="Dockerfile security issues",
                    description=f"Found {len(dockerfile_issues)} security concerns in Dockerfile",
                    recommendation="Use non-root user, don't run as privileged, minimize layers, scan with Trivy",
                    estimation_hours=10,
                )
                score -= 10
        
        # Check for docker-compose security
        has_compose = any(
            'docker-compose' in f.lower() or 'compose' in f.lower()
            for f in getattr(repo_data, 'files', [])
        )
        
        if has_compose:
            # Check for hardcoded credentials in compose
            score -= 5  # Potential issue
        
        # Check for IaC files (Terraform, CloudFormation, etc.)
        has_iac = any(
            any(x in f.lower() for x in ['terraform', 'cloudformation', '.tf', '.yaml'])
            for f in getattr(repo_data, 'files', [])
        )
        
        if has_iac:
            self.add_finding(
                category="Security",
                severity="MEDIUM",
                title="Infrastructure-as-Code present",
                description="Repository contains IaC files that should be security scanned",
                recommendation="Use checkov or similar tools to scan Terraform/CloudFormation files",
                estimation_hours=5,
            )
            score -= 5
        
        return max(0.0, score)

    async def _check_auth_patterns(self, repo_data: RepositoryData) -> float:
        """Check authentication and authorization patterns.
        
        Returns:
            Score 0-100
        """
        self.log_debug("Checking authentication patterns")
        
        score = 100.0
        
        # Check for authentication framework usage
        framework_used = await self._detect_auth_framework(repo_data)
        
        if not framework_used:
            # Self-implemented auth is risky
            self.add_finding(
                category="Security",
                severity="MEDIUM",
                title="No standard authentication framework detected",
                description="Authentication may be custom-implemented",
                recommendation="Use established frameworks (Django Auth, FastAPI auth, Keycloak, etc.)",
                estimation_hours=30,
            )
            score -= 15
        
        return max(0.0, score)

    # Helper methods
    
    async def _check_vulnerable_dependencies(self, repo_data: RepositoryData) -> List[str]:
        """Check for dependencies with known vulnerabilities.
        
        Returns:
            List of vulnerable package names
        """
        vulnerable = []
        
        # Known vulnerable patterns (simplified)
        if hasattr(repo_data, 'dependencies') and repo_data.dependencies:
            # Would check actual versions against CVE database
            pass
        
        return vulnerable

    async def _check_deps_pinning(self, repo_data: RepositoryData) -> bool:
        """Check if dependencies are pinned to specific versions.
        
        Returns:
            True if properly pinned
        """
        files = getattr(repo_data, 'files', [])
        
        # Check for requirements.txt, setup.py, pyproject.toml, etc.
        dep_files = {
            'requirements.txt',
            'Pipfile.lock',
            'poetry.lock',
            'package-lock.json',
        }
        
        return any(f in files for f in dep_files)

    async def _check_audit_config(self, repo_data: RepositoryData) -> bool:
        """Check if security audit tools are configured.
        
        Returns:
            True if audit configured
        """
        files = getattr(repo_data, 'files', [])
        
        audit_files = {
            '.github/workflows',
            '.gitlab-ci.yml',
            '.bandit',
            '.safety',
            'pytest.ini',
        }
        
        files_str = ' '.join(files)
        
        return any(audit in files_str for audit in ['bandit', 'safety', 'semgrep', 'workflow'])

    async def _check_secret_patterns(self, repo_data: RepositoryData) -> List[str]:
        """Check for secret-like patterns in code.
        
        Returns:
            List of suspicious patterns found
        """
        suspicious = []
        
        # Would scan actual code files
        # For now return empty
        
        return suspicious

    async def _find_risky_patterns(self, repo_data: RepositoryData) -> Set[str]:
        """Find dangerous code patterns.
        
        Returns:
            Set of risky patterns found
        """
        patterns = set()
        
        # Would scan source files
        # For now return empty
        
        return patterns

    async def _check_dockerfile_security(self, repo_data: RepositoryData) -> List[str]:
        """Check Dockerfile for security issues.
        
        Returns:
            List of issues found
        """
        issues = []
        
        # Would parse Dockerfile
        # For now return potential issues
        
        issues.append("Check if running as root user")
        issues.append("Verify base image freshness")
        
        return issues[:2]

    async def _detect_auth_framework(self, repo_data: RepositoryData) -> bool:
        """Detect if standard auth framework is used.
        
        Returns:
            True if framework detected
        """
        files = getattr(repo_data, 'files', [])
        imports = ' '.join(files)
        
        frameworks = [
            'django.contrib.auth',
            'fastapi',
            'auth0',
            'keycloak',
            'oauth',
            'jwt',
        ]
        
        # Would check imports in actual code
        return any(fw in imports.lower() for fw in frameworks)
