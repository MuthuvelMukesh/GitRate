"""Master audit orchestrator for coordinating all auditors."""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum

from gitrate.core.models import (
    RepositoryData, AcquisitionAuditResult, AuditScores,
    FinancialImpact, ComplianceCertificate, AuditFinding,
    RoadmapTask
)
from gitrate.integrations.github_api import GitHubFetcher
from gitrate.utils.helpers import calculate_risk_score, estimate_hours_to_fix
from gitrate.utils.constants import RISK_THRESHOLDS
from gitrate.auditors import (
    IPLegalAuditor,
    TeamSustainabilityAuditor,
    CodeQualityAuditor,
    SecurityAuditor,
)
from gitrate.reports import (
    PDFReportGenerator,
    ComplianceCertificateGenerator,
    RoadmapGenerator,
)

logger = logging.getLogger(__name__)


class AuditStatus(str, Enum):
    """Audit execution status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AuditEngine:
    """Master orchestrator for acquisition audits."""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize audit engine.
        
        Args:
            github_token: GitHub API token
        """
        self.github_token = github_token
        self.github_fetcher = GitHubFetcher(github_token)
        
        # Track active audits
        self.active_audits: Dict[str, Dict[str, Any]] = {}
    
    async def run_full_audit(
        self,
        owner: str,
        repo: str,
    ) -> tuple[Optional[AcquisitionAuditResult], Optional[str]]:
        """
        Run complete acquisition audit on repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Tuple of (AcquisitionAuditResult, error_message)
        """
        audit_id = str(uuid.uuid4())[:8]
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting audit {audit_id} for {owner}/{repo}")
            self.active_audits[audit_id] = {
                "status": AuditStatus.IN_PROGRESS,
                "owner": owner,
                "repo": repo,
                "start_time": start_time,
            }
            
            # Step 1: Fetch repository data
            logger.info(f"[{audit_id}] Step 1: Fetching repository data...")
            repo_data, fetch_error = await self.github_fetcher.fetch_repository_data(owner, repo)
            
            if fetch_error:
                error_msg = f"Failed to fetch repository data: {fetch_error}"
                logger.error(f"[{audit_id}] {error_msg}")
                self.active_audits[audit_id]["status"] = AuditStatus.FAILED
                return None, error_msg
            
            logger.info(f"[{audit_id}] Successfully fetched repository data")
            
            # Step 2: Initialize audit findings
            all_findings: List[AuditFinding] = []
            scores_dict: Dict[str, float] = {}
            
            # Step 3: Run IP & Legal audit (STUB)
            logger.info(f"[{audit_id}] Step 2: Running IP & Legal audit...")
            ip_score, ip_findings = await self._audit_ip_legal(repo_data)
            scores_dict["ip_legal"] = ip_score
            all_findings.extend(ip_findings)
            
            # Step 4: Run Team audit (STUB)
            logger.info(f"[{audit_id}] Step 3: Running Team audit...")
            team_score, team_findings = await self._audit_team_sustainability(repo_data)
            scores_dict["team_sustainability"] = team_score
            all_findings.extend(team_findings)
            
            # Step 5: Run Code Quality audit (STUB)
            logger.info(f"[{audit_id}] Step 4: Running Code Quality audit...")
            quality_score, quality_findings = await self._audit_code_quality(repo_data)
            scores_dict["code_quality"] = quality_score
            all_findings.extend(quality_findings)
            
            # Step 6: Run Security audit (STUB)
            logger.info(f"[{audit_id}] Step 5: Running Security audit...")
            security_score, security_findings = await self._audit_security(repo_data)
            scores_dict["security"] = security_score
            all_findings.extend(security_findings)
            
            # Step 7: Calculate overall score
            overall_score = self._calculate_overall_score(scores_dict)
            
            # Step 8: Generate compliance certificate
            compliance = self._generate_compliance_certificate(scores_dict, all_findings)
            
            # Step 9: Calculate financial impact
            financial_impact = self._calculate_financial_impact(all_findings, repo_data)
            
            # Step 10: Generate 90-day roadmap
            roadmap = self._generate_90day_roadmap(all_findings)
            
            # Step 11: Generate executive summary
            executive_summary = self._generate_executive_summary(scores_dict, all_findings)
            go_no_go = self._determine_go_no_go(scores_dict, all_findings)
            
            # Step 12: Compile final result
            audit_duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = AcquisitionAuditResult(
                audit_id=audit_id,
                repository=f"{owner}/{repo}",
                audit_date=start_time,
                audit_duration_seconds=int(audit_duration),
                
                scores=AuditScores(
                    ip_legal=scores_dict["ip_legal"],
                    team_sustainability=scores_dict["team_sustainability"],
                    code_quality=scores_dict["code_quality"],
                    security=scores_dict["security"],
                    overall=overall_score,
                ),
                
                findings=all_findings,
                critical_findings=[f for f in all_findings if f.severity == "CRITICAL"],
                red_flags=self._extract_red_flags(all_findings),
                
                financial_impact=financial_impact,
                compliance=compliance,
                
                executive_summary=executive_summary,
                go_no_go_recommendation=go_no_go,
                
                roadmap_90_day=roadmap,
                repository_data=repo_data,
            )
            
            self.active_audits[audit_id]["status"] = AuditStatus.COMPLETED
            
            logger.info(f"[{audit_id}] Audit completed successfully in {audit_duration:.1f}s")
            return result, None
            
        except Exception as e:
            error = f"Unexpected error during audit: {str(e)}"
            logger.error(f"[{audit_id}] {error}", exc_info=True)
            self.active_audits[audit_id]["status"] = AuditStatus.FAILED
            return None, error
    
    # ===== PHASE 3: REAL AUDITORS =====
    
    async def _audit_ip_legal(
        self,
        repo_data: RepositoryData,
    ) -> tuple[float, List[AuditFinding]]:
        """Run IP & Legal audit using real implementation."""
        try:
            auditor = IPLegalAuditor()
            score, findings = await auditor.run(repo_data)
            logger.debug(f"IP & Legal audit completed: {score:.1f}/100 with {len(findings)} findings")
            return score, findings
        except Exception as e:
            logger.error(f"IP & Legal audit failed: {str(e)}", exc_info=True)
            return 75.0, []
    
    async def _audit_team_sustainability(
        self,
        repo_data: RepositoryData,
    ) -> tuple[float, List[AuditFinding]]:
        """Run Team Sustainability audit using real implementation."""
        try:
            auditor = TeamSustainabilityAuditor()
            score, findings = await auditor.run(repo_data)
            logger.debug(f"Team Sustainability audit completed: {score:.1f}/100 with {len(findings)} findings")
            return score, findings
        except Exception as e:
            logger.error(f"Team Sustainability audit failed: {str(e)}", exc_info=True)
            return 70.0, []
    
    async def _audit_code_quality(
        self,
        repo_data: RepositoryData,
    ) -> tuple[float, List[AuditFinding]]:
        """Run Code Quality audit using real implementation."""
        try:
            auditor = CodeQualityAuditor()
            score, findings = await auditor.run(repo_data)
            logger.debug(f"Code Quality audit completed: {score:.1f}/100 with {len(findings)} findings")
            return score, findings
        except Exception as e:
            logger.error(f"Code Quality audit failed: {str(e)}", exc_info=True)
            return 65.0, []
    
    async def _audit_security(
        self,
        repo_data: RepositoryData,
    ) -> tuple[float, List[AuditFinding]]:
        """Run Security audit using real implementation."""
        try:
            auditor = SecurityAuditor()
            score, findings = await auditor.run(repo_data)
            logger.debug(f"Security audit completed: {score:.1f}/100 with {len(findings)} findings")
            return score, findings
        except Exception as e:
            logger.error(f"Security audit failed: {str(e)}", exc_info=True)
            return 72.0, []
    
    # ===== HELPER METHODS =====
    
    @staticmethod
    def _calculate_overall_score(scores: Dict[str, float]) -> float:
        """Calculate overall audit score from component scores."""
        if not scores:
            return 0.0
        
        # Weighted average (can adjust weights)
        weights = {
            "ip_legal": 0.30,  # Highest priority
            "security": 0.25,
            "code_quality": 0.25,
            "team_sustainability": 0.20,
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric, score in scores.items():
            weight = weights.get(metric, 0.25)
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_sum / total_weight
    
    @staticmethod
    def _generate_compliance_certificate(
        scores: Dict[str, float],
        findings: List[AuditFinding],
    ) -> ComplianceCertificate:
        """Generate compliance certificate with RED/YELLOW/GREEN ratings."""
        
        def get_compliance_status(score: float, critical_count: int) -> str:
            if critical_count > 0 or score < 50:
                return "RED"
            elif score < 70:
                return "YELLOW"
            else:
                return "GREEN"
        
        critical_count = len([f for f in findings if f.severity == "CRITICAL"])
        
        return ComplianceCertificate(
            legal_compliance=get_compliance_status(scores.get("ip_legal", 0), critical_count),
            security_compliance=get_compliance_status(scores.get("security", 0), critical_count),
            team_sustainability=get_compliance_status(scores.get("team_sustainability", 0), 0),
            code_quality=get_compliance_status(scores.get("code_quality", 0), 0),
            overall_compliance=get_compliance_status(
                sum(scores.values()) / len(scores) if scores else 0,
                critical_count
            ),
        )
    
    @staticmethod
    def _calculate_financial_impact(
        findings: List[AuditFinding],
        repo_data: RepositoryData,
    ) -> FinancialImpact:
        """Calculate financial impact of findings."""
        
        # Sum estimation hours from all findings
        total_debt_hours = sum(f.estimation_hours or 0 for f in findings)
        
        # Convert hours to cost ($100/hour is standard rate)
        debt_cost = total_debt_hours * 100
        
        # Risk multipliers
        critical_count = len([f for f in findings if f.severity == "CRITICAL"])
        compliance_risk = critical_count * 25000
        security_risk = (critical_count * 50000) + (len(findings) * 1000)
        team_risk = 100000 if repo_data.contributors.total_contributors < 3 else 20000
        
        total_risk = debt_cost + compliance_risk + security_risk + team_risk
        
        # Valuation discount (rough estimate)
        annual_revenue_estimate = 1000000  # Default assumption
        valuation_discount = min(30, (total_risk / annual_revenue_estimate) * 100)
        
        return FinancialImpact(
            technical_debt_cost_usd=float(debt_cost),
            compliance_risk_cost_usd=float(compliance_risk),
            security_risk_cost_usd=float(security_risk),
            team_risk_cost_usd=float(team_risk),
            total_risk_usd=float(total_risk),
            valuation_discount_percent=valuation_discount,
        )
    
    @staticmethod
    def _generate_90day_roadmap(findings: List[AuditFinding]) -> List[RoadmapTask]:
        """Generate 90-day stabilization roadmap."""
        
        tasks = [
            RoadmapTask(
                phase=1,
                week_range="1-2",
                title="Immediate Security Hardening",
                description="Rotate secrets, enable 2FA, apply critical security patches",
                estimated_hours=40,
                owner_role="DevOps / Security",
                success_criteria="All critical CVEs patched, secrets rotated",
                priority="CRITICAL",
            ),
            RoadmapTask(
                phase=1,
                week_range="1-2",
                title="Establish Development Baseline",
                description="Document current architecture, code quality metrics, test coverage",
                estimated_hours=30,
                owner_role="Tech Lead / DevOps",
                success_criteria="Baseline documentation complete",
                priority="HIGH",
            ),
            RoadmapTask(
                phase=2,
                week_range="3-6",
                title="Improve Test Coverage",
                description="Add tests for critical paths, reach 60%+ coverage",
                estimated_hours=120,
                owner_role="Backend / Frontend / QA",
                success_criteria="Test coverage >60%, all critical paths covered",
                priority="HIGH",
            ),
            RoadmapTask(
                phase=2,
                week_range="3-6",
                title="Stabilize CI/CD Pipeline",
                description="Fix failing tests, improve build time, enable automated deployment",
                estimated_hours=60,
                owner_role="DevOps",
                success_criteria="All tests passing, deployment automated",
                priority="HIGH",
            ),
            RoadmapTask(
                phase=3,
                week_range="7-12",
                title="Refactor High-Risk Modules",
                description="Refactor top 3 'bug factories' (high churn + complexity)",
                estimated_hours=160,
                owner_role="Backend / Frontend",
                success_criteria="Complexity reduced, code review passed",
                priority="MEDIUM",
            ),
            RoadmapTask(
                phase=3,
                week_range="7-12",
                title="Knowledge Transfer & Documentation",
                description="Document architecture, onboard key people, create runbooks",
                estimated_hours=80,
                owner_role="Tech Lead / All",
                success_criteria="Knowledge transfer complete, runbooks available",
                priority="MEDIUM",
            ),
        ]
        
        return tasks
    
    @staticmethod
    def _extract_red_flags(findings: List[AuditFinding]) -> List[str]:
        """Extract top 5 red flags from findings."""
        
        critical_findings = [f for f in findings if f.severity == "CRITICAL"]
        critical_findings.sort(key=lambda f: f.estimation_hours or 0, reverse=True)
        
        red_flags = [f.title for f in critical_findings[:5]]
        
        return red_flags
    
    @staticmethod
    def _generate_executive_summary(
        scores: Dict[str, float],
        findings: List[AuditFinding],
    ) -> str:
        """Generate executive summary."""
        
        overall = sum(scores.values()) / len(scores) if scores else 0
        critical_count = len([f for f in findings if f.severity == "CRITICAL"])
        
        summary = (
            f"Technical audit scored {overall:.0f}/100 overall. "
            f"Found {critical_count} critical issues requiring immediate attention. "
            f"IP/Legal score: {scores.get('ip_legal', 0):.0f}, "
            f"Security score: {scores.get('security', 0):.0f}. "
            f"Primary risks include knowledge concentration and technical debt. "
            f"Recommend 90-day stabilization roadmap post-acquisition."
        )
        
        return summary
    
    @staticmethod
    def _determine_go_no_go(
        scores: Dict[str, float],
        findings: List[AuditFinding],
    ) -> str:
        """Determine go/caution/no-go recommendation."""
        
        overall = sum(scores.values()) / len(scores) if scores else 0
        critical_count = len([f for f in findings if f.severity == "CRITICAL"])
        
        if overall >= 75 and critical_count == 0:
            return "GREEN - Proceed with acquisition"
        elif overall >= 60 and critical_count <= 2:
            return "YELLOW - Conditional proceed with risk mitigation"
        else:
            return "RED - Address critical issues before acquisition"
    
    # ===== REPORT GENERATION =====
    
    async def generate_pdf_report(self, audit_result: AcquisitionAuditResult) -> Tuple[bytes, str]:
        """Generate professional PDF report.
        
        Args:
            audit_result: Complete audit result
        
        Returns:
            Tuple of (PDF bytes, filename)
        """
        try:
            logger.info(f"[{audit_result.audit_id}] Generating PDF report")
            
            generator = PDFReportGenerator(audit_result)
            pdf_bytes = await generator.generate()
            
            filename = f"GitRate_Audit_{audit_result.repository.replace('/', '_')}_{audit_result.audit_id}.pdf"
            
            logger.info(f"[{audit_result.audit_id}] PDF report generated: {len(pdf_bytes)} bytes")
            return pdf_bytes, filename
            
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}", exc_info=True)
            raise
    
    async def generate_compliance_certificate(self, audit_result: AcquisitionAuditResult) -> Tuple[bytes, str]:
        """Generate compliance certificate.
        
        Args:
            audit_result: Complete audit result
        
        Returns:
            Tuple of (PDF bytes, filename)
        """
        try:
            logger.info(f"[{audit_result.audit_id}] Generating compliance certificate")
            
            generator = ComplianceCertificateGenerator(audit_result)
            cert_bytes = await generator.generate()
            
            filename = f"GitRate_Certificate_{audit_result.audit_id}.pdf"
            
            logger.info(f"[{audit_result.audit_id}] Certificate generated: {len(cert_bytes)} bytes")
            return cert_bytes, filename
            
        except Exception as e:
            logger.error(f"Certificate generation failed: {str(e)}", exc_info=True)
            raise
    
    async def generate_remediation_roadmap(self, audit_result: AcquisitionAuditResult,
                                          team_size: int = 3) -> Tuple[List[RoadmapTask], str]:
        """Generate 90-day remediation roadmap.
        
        Args:
            audit_result: Complete audit result
            team_size: Size of remediation team
        
        Returns:
            Tuple of (list of tasks, summary text)
        """
        try:
            logger.info(f"[{audit_result.audit_id}] Generating remediation roadmap")
            
            generator = RoadmapGenerator(audit_result, team_size=team_size)
            roadmap_tasks = await generator.generate()
            
            summary = generator.get_executive_summary(roadmap_tasks)
            
            logger.info(f"[{audit_result.audit_id}] Roadmap generated with {len(roadmap_tasks)} tasks")
            return roadmap_tasks, summary
            
        except Exception as e:
            logger.error(f"Roadmap generation failed: {str(e)}", exc_info=True)
            raise
    
    async def generate_all_reports(self, audit_result: AcquisitionAuditResult, 
                                   team_size: int = 3) -> Dict[str, Any]:
        """Generate all reports in one call.
        
        Args:
            audit_result: Complete audit result
            team_size: Size of remediation team
        
        Returns:
            Dict with all generated reports
        """
        logger.info(f"[{audit_result.audit_id}] Generating all reports")
        
        try:
            # Generate PDF
            pdf_bytes, pdf_filename = await self.generate_pdf_report(audit_result)
            
            # Generate certificate
            cert_bytes, cert_filename = await self.generate_compliance_certificate(audit_result)
            
            # Generate roadmap
            roadmap_tasks, roadmap_summary = await self.generate_remediation_roadmap(
                audit_result, team_size
            )
            
            result = {
                "pdf": {
                    "content": pdf_bytes,
                    "filename": pdf_filename,
                    "size": len(pdf_bytes),
                },
                "certificate": {
                    "content": cert_bytes,
                    "filename": cert_filename,
                    "size": len(cert_bytes),
                },
                "roadmap": {
                    "tasks": roadmap_tasks,
                    "summary": roadmap_summary,
                    "task_count": len(roadmap_tasks),
                },
                "generated_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"[{audit_result.audit_id}] All reports generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}", exc_info=True)
            raise
