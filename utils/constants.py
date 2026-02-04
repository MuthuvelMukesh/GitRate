"""Constants and configuration for GitRate."""

from enum import Enum
from typing import Final

# ===== AUDIT CONSTANTS =====
AUDIT_TIMEOUT_SECONDS: Final[int] = 300  # 5 minutes max audit time
MAX_REPO_SIZE_MB: Final[int] = 500
CACHE_AUDIT_RESULTS: Final[bool] = True
AUDIT_CACHE_TTL_HOURS: Final[int] = 24

# ===== DEPENDENCY ANALYSIS =====
DEPENDENCY_FILES = {
    "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "poetry.lock"],
    "javascript": ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "go": ["go.mod", "go.sum"],
    "rust": ["Cargo.toml", "Cargo.lock"],
    "ruby": ["Gemfile", "Gemfile.lock"],
    "php": ["composer.json", "composer.lock"],
}

CI_CD_FILES = {
    "github": ".github/workflows/",
    "gitlab": ".gitlab-ci.yml",
    "circleci": ".circleci/config.yml",
    "jenkins": "Jenkinsfile",
    "travisci": ".travis.yml",
    "appveyor": "appveyor.yml",
    "azure": "azure-pipelines.yml",
}

# ===== LICENSE CATEGORIES =====
VIRAL_LICENSES = {
    "GPL",
    "AGPL",
    "SSPL",
}

PERMISSIVE_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "MPL-2.0",
}

PROPRIETARY_LICENSES = {
    "Proprietary",
    "Commercial",
    "Unlicense",
}

# ===== RISK THRESHOLDS =====
class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


RISK_THRESHOLDS = {
    "ip_legal": {
        "CRITICAL": 80,
        "HIGH": 60,
        "MEDIUM": 40,
        "LOW": 0,
    },
    "team_sustainability": {
        "CRITICAL": 80,
        "HIGH": 60,
        "MEDIUM": 40,
        "LOW": 0,
    },
    "code_quality": {
        "CRITICAL": 80,
        "HIGH": 60,
        "MEDIUM": 40,
        "LOW": 0,
    },
    "security": {
        "CRITICAL": 80,
        "HIGH": 60,
        "MEDIUM": 40,
        "LOW": 0,
    },
}

# ===== BUS FACTOR THRESHOLDS =====
BUS_FACTOR_CRITICAL: Final[int] = 2  # If ≤2 people leave, project is at risk
BUS_FACTOR_HIGH: Final[int] = 3
BUS_FACTOR_MEDIUM: Final[int] = 5

# ===== CODE QUALITY THRESHOLDS =====
KNOWLEDGE_SILO_THRESHOLD: Final[float] = 0.70  # 70% commits by one person
TEST_COVERAGE_TARGET: Final[int] = 80
CYCLOMATIC_COMPLEXITY_HIGH: Final[int] = 10
CYCLOMATIC_COMPLEXITY_CRITICAL: Final[int] = 20

# ===== TECHNICAL DEBT ESTIMATION =====
DEBT_ESTIMATION = {
    "dependency_update_per_lib_hours": 20,
    "test_coverage_gap_hours": 40,
    "high_complexity_file_hours": 10,
    "dead_code_removal_hours": 5,
    "security_hardening_hours": 30,
    "refactoring_per_100_loc_hours": 5,
}

# ===== CVE THRESHOLDS =====
CVE_AGE_CRITICAL_DAYS: Final[int] = 90  # Unfixed for >90 days = CRITICAL
CVE_AGE_HIGH_DAYS: Final[int] = 60
CVE_AGE_MEDIUM_DAYS: Final[int] = 30

CVE_SEVERITY_WEIGHTS = {
    "CRITICAL": 10,
    "HIGH": 5,
    "MEDIUM": 2,
    "LOW": 1,
}

# ===== GITHUB API =====
GITHUB_API_BASE_URL: Final[str] = "https://api.github.com"
GITHUB_RATE_LIMIT_REQUESTS: Final[int] = 60  # Per minute for authenticated
GITHUB_RATE_LIMIT_RESET_SECONDS: Final[int] = 60

# ===== CACHE KEYS =====
CACHE_KEY_REPO_DATA: Final[str] = "repo:{owner}:{repo}"
CACHE_KEY_AUDIT_RESULT: Final[str] = "audit:{owner}:{repo}"
CACHE_KEY_CVE_DATA: Final[str] = "cve:{package}:{version}"

# ===== DEFAULTS =====
DEFAULT_REPO_LANGUAGE: Final[str] = "unknown"
DEFAULT_TIMEOUT_SECONDS: Final[int] = 30
