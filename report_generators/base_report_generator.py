"""Base report generator class providing shared functionality for all report types."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from logging import getLogger
from datetime import datetime
from io import BytesIO

from core.models import AcquisitionAuditResult, AuditFinding

logger = getLogger(__name__)


class BaseReportGenerator(ABC):
    """Base class for all report generators.
    
    Provides common functionality for:
    - Report metadata and formatting
    - Finding categorization and sorting
    - Styling and branding
    - Output generation
    """

    def __init__(self, 
                 audit_result: AcquisitionAuditResult,
                 company_name: str = "GitRate",
                 branding_color: str = "#2563eb"):
        """Initialize report generator.
        
        Args:
            audit_result: Complete audit result object
            company_name: Organization name for branding
            branding_color: Primary color in hex format
        """
        self.audit_result = audit_result
        self.company_name = company_name
        self.branding_color = branding_color
        self.logo_url = "https://gitrate.io/logo.png"  # Placeholder
        
        logger.debug(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    async def generate(self) -> bytes:
        """Generate report output.
        
        Returns:
            Report as bytes (PDF, HTML, etc.)
        """
        pass

    def _categorize_findings(self) -> Dict[str, List[AuditFinding]]:
        """Organize findings by category.
        
        Returns:
            Dict mapping category -> sorted findings
        """
        categorized = {}
        
        for finding in self.audit_result.findings:
            category = finding.category
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(finding)
        
        # Sort by severity (CRITICAL first)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        
        for category in categorized:
            categorized[category].sort(
                key=lambda f: severity_order.get(f.severity, 4)
            )
        
        return categorized

    def _get_critical_findings(self) -> List[AuditFinding]:
        """Get all critical findings sorted by impact.
        
        Returns:
            List of critical findings
        """
        return [f for f in self.audit_result.findings if f.severity == "CRITICAL"]

    def _get_high_findings(self) -> List[AuditFinding]:
        """Get all high-severity findings.
        
        Returns:
            List of high-severity findings
        """
        return [f for f in self.audit_result.findings if f.severity == "HIGH"]

    def _calculate_remediation_hours(self) -> int:
        """Calculate total estimated remediation hours.
        
        Returns:
            Sum of all estimation_hours in findings
        """
        return sum(f.estimation_hours for f in self.audit_result.findings)

    def _calculate_remediation_cost(self, hourly_rate: float = 150.0) -> float:
        """Estimate remediation cost at given hourly rate.
        
        Args:
            hourly_rate: Cost per hour (default: $150/hr consultant rate)
        
        Returns:
            Total estimated cost in dollars
        """
        hours = self._calculate_remediation_hours()
        return hours * hourly_rate

    def _format_score(self, score: float) -> str:
        """Format score as colored text representation.
        
        Args:
            score: Score 0-100
        
        Returns:
            Formatted score string
        """
        if score >= 80:
            status = "EXCELLENT"
            symbol = "🟢"
        elif score >= 60:
            status = "GOOD"
            symbol = "🟡"
        elif score >= 40:
            status = "NEEDS ATTENTION"
            symbol = "🟠"
        else:
            status = "CRITICAL"
            symbol = "🔴"
        
        return f"{symbol} {score:.1f}/100 ({status})"

    def _get_score_description(self, score: float) -> str:
        """Get description for a score range.
        
        Args:
            score: Score 0-100
        
        Returns:
            Description string
        """
        if score >= 85:
            return "Excellent - minimal risk"
        elif score >= 70:
            return "Good - acceptable risk with minor fixes"
        elif score >= 55:
            return "Moderate - requires attention in multiple areas"
        elif score >= 40:
            return "Poor - significant concerns across domains"
        else:
            return "Critical - major remediation required before acquisition"

    def _get_recommendation_details(self) -> Dict[str, Any]:
        """Generate detailed recommendation based on scores and findings.
        
        Returns:
            Dict with recommendation details
        """
        go_no_go = self.audit_result.go_no_go_recommendation
        scores = self.audit_result.scores
        critical = len(self._get_critical_findings())
        high = len(self._get_high_findings())
        
        return {
            "recommendation": go_no_go,
            "overall_score": scores.overall,
            "critical_findings": critical,
            "high_findings": high,
            "total_findings": len(self.audit_result.findings),
            "remediation_hours": self._calculate_remediation_hours(),
            "remediation_cost": self._calculate_remediation_cost(),
        }

    def _format_finding_severity(self, severity: str) -> str:
        """Format severity level with emoji.
        
        Args:
            severity: CRITICAL, HIGH, MEDIUM, LOW
        
        Returns:
            Formatted severity string
        """
        icons = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }
        return f"{icons.get(severity, '●')} {severity}"

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime in human-readable format.
        
        Args:
            dt: Datetime object
        
        Returns:
            Formatted date string
        """
        return dt.strftime("%B %d, %Y at %H:%M UTC")

    def _estimate_review_time(self) -> int:
        """Estimate minutes needed to review this report.
        
        Returns:
            Estimated minutes
        """
        # Base time + time per finding
        base_minutes = 15
        per_finding = 2
        critical_factor = len(self._get_critical_findings()) * 5
        
        return base_minutes + (len(self.audit_result.findings) * per_finding) + critical_factor

    def log_debug(self, message: str) -> None:
        """Log debug message with report context."""
        logger.debug(f"[{self.__class__.__name__}] {message}")

    def log_info(self, message: str) -> None:
        """Log info message with report context."""
        logger.info(f"[{self.__class__.__name__}] {message}")

    def log_error(self, message: str) -> None:
        """Log error message with report context."""
        logger.error(f"[{self.__class__.__name__}] {message}")
