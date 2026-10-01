"""Base auditor class providing shared functionality for all audit modules."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from logging import getLogger

from gitrate.core.models import (
    AuditFinding,
    RepositoryData,
)

logger = getLogger(__name__)


class BaseAuditor(ABC):
    """Base class for all audit modules.
    
    Provides common functionality for:
    - Finding generation with standardized formatting
    - Score calculation with severity weighting
    - Error handling and logging
    - Performance tracking
    """

    def __init__(self, name: str):
        """Initialize auditor with name and default configuration."""
        self.name = name
        self.findings: List[AuditFinding] = []
        self.base_score = 100.0
        self.debug_info: Dict[str, Any] = {}

    @abstractmethod
    async def run(self, repo_data: RepositoryData) -> tuple[float, List[AuditFinding]]:
        """Run the audit analysis.
        
        Args:
            repo_data: Complete repository data from fetcher
            
        Returns:
            Tuple of (audit_score, findings_list)
            - Score: 0-100 float
            - Findings: List of AuditFinding objects
        """
        pass

    def add_finding(
        self,
        category: str,
        severity: str,
        title: str,
        description: str,
        recommendation: str,
        estimation_hours: float = 0.0,
        remediation_priority: str = "MEDIUM",
    ) -> None:
        """Add a finding with standardized validation.
        
        Args:
            category: Audit category (e.g., "License", "Security")
            severity: HIGH, MEDIUM, LOW
            title: Short finding title
            description: Detailed description
            recommendation: How to fix it
            estimation_hours: Time to remediate
            remediation_priority: CRITICAL, HIGH, MEDIUM, LOW
        """
        finding = AuditFinding(
            category=category,
            severity=severity,
            title=title,
            description=description,
            recommendation=recommendation,
            estimation_hours=estimation_hours,
            remediation_priority=remediation_priority,
        )
        self.findings.append(finding)
        logger.debug(f"[{self.name}] Added {severity} finding: {title}")

    def calculate_score_with_penalties(
        self,
        base_score: float,
        severity_penalties: Dict[str, float],
    ) -> float:
        """Calculate audit score with severity-based penalties.
        
        Args:
            base_score: Starting score (e.g., 100.0)
            severity_penalties: Dict mapping severity -> penalty amount
                e.g., {"CRITICAL": 25, "HIGH": 10, "MEDIUM": 5}
        
        Returns:
            Final score (0-100) after penalties applied
        """
        score = base_score
        
        for finding in self.findings:
            penalty = severity_penalties.get(finding.severity, 0)
            score -= penalty
        
        # Ensure score stays in bounds
        return max(0.0, min(100.0, score))

    def calculate_score_weighted(
        self,
        criteria: Dict[str, tuple[bool, float]],
    ) -> float:
        """Calculate score using weighted criteria evaluation.
        
        Args:
            criteria: Dict of {criterion_name: (is_passed: bool, weight: float)}
        
        Returns:
            Weighted score 0-100
        """
        total_weight = sum(weight for _, weight in criteria.values())
        if total_weight == 0:
            return 50.0  # Default if no criteria
        
        earned_weight = sum(
            weight for is_passed, weight in criteria.values()
            if is_passed
        )
        
        return (earned_weight / total_weight) * 100.0

    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug information with auditor context."""
        logger.debug(f"[{self.name}] {message}", extra=kwargs)

    def log_info(self, message: str) -> None:
        """Log info message with auditor context."""
        logger.info(f"[{self.name}] {message}")

    def log_warning(self, message: str) -> None:
        """Log warning message with auditor context."""
        logger.warning(f"[{self.name}] {message}")

    def log_error(self, message: str) -> None:
        """Log error message with auditor context."""
        logger.error(f"[{self.name}] {message}")
