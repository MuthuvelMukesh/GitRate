"""
Insights Generation Engine for GitRate Platform - Phase 7

Generates:
- Automated improvement recommendations
- Risk alerts
- Performance patterns
- Benchmark comparisons
- Anomaly reports
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import statistics

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """Represents a single insight"""
    id: str
    title: str
    description: str
    category: str  # "risk", "opportunity", "anomaly", "trend", "benchmark"
    severity: str  # "critical", "high", "medium", "low", "info"
    confidence: float  # 0-1
    affected_repositories: List[str]
    recommendations: List[str]
    evidence: Dict
    generated_at: datetime


@dataclass
class InsightReport:
    """Complete insight report for repositories"""
    generated_at: datetime
    report_period_days: int
    total_insights: int
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    insights: List[Insight]
    executive_summary: str


class InsightsEngine:
    """
    Generates intelligent insights from audit data
    
    Features:
    - Risk detection (security, quality, team)
    - Opportunity identification
    - Anomaly reporting
    - Trend analysis
    - Benchmark comparisons
    """
    
    def __init__(self):
        self.insights = []
        self.repository_data = {}
    
    def add_repository_data(self, repository: str, audit_history: List[Dict]):
        """Store audit history for analysis"""
        self.repository_data[repository] = audit_history
    
    def generate_insights(self, 
                         repository: str,
                         current_audit: Dict,
                         historical_audits: List[Dict],
                         peer_data: Dict) -> List[Insight]:
        """
        Generate insights for a repository
        
        Args:
            repository: Repository name
            current_audit: Current audit metrics
            historical_audits: List of previous audits
            peer_data: Peer repositories for benchmarking
        
        Returns:
            List of Insight objects
        """
        
        insights = []
        
        # Risk Insights
        insights.extend(self._identify_risk_insights(repository, current_audit, historical_audits))
        
        # Opportunity Insights
        insights.extend(self._identify_opportunity_insights(repository, current_audit))
        
        # Anomaly Insights
        insights.extend(self._identify_anomaly_insights(repository, current_audit, historical_audits))
        
        # Trend Insights
        insights.extend(self._identify_trend_insights(repository, historical_audits))
        
        # Benchmark Insights
        insights.extend(self._identify_benchmark_insights(repository, current_audit, peer_data))
        
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        insights.sort(key=lambda x: severity_order.get(x.severity, 5))
        
        return insights
    
    def _identify_risk_insights(self, repository: str, current: Dict, history: List[Dict]) -> List[Insight]:
        """Identify risk-related insights"""
        insights = []
        
        # Security risk
        if current.get('security_score', 100) < 60:
            insights.append(Insight(
                id=f"security_risk_{repository}",
                title="Security Score Below Threshold",
                description=f"Security score of {current['security_score']} indicates potential vulnerabilities",
                category="risk",
                severity="critical" if current['security_score'] < 40 else "high",
                confidence=0.95,
                affected_repositories=[repository],
                recommendations=[
                    "Review security audit findings in detail",
                    "Implement security improvements from recommendations",
                    "Schedule security code review",
                    "Enable security scanning in CI/CD"
                ],
                evidence={
                    "current_score": current['security_score'],
                    "threshold": 60,
                    "findings_count": current.get('critical_findings', 0)
                },
                generated_at=datetime.now()
            ))
        
        # Quality risk
        if current.get('code_quality_score', 100) < 60:
            insights.append(Insight(
                id=f"quality_risk_{repository}",
                title="Code Quality Score Below Threshold",
                description=f"Code quality score of {current['code_quality_score']} indicates potential maintainability issues",
                category="risk",
                severity="high",
                confidence=0.90,
                affected_repositories=[repository],
                recommendations=[
                    "Increase test coverage",
                    "Reduce code complexity",
                    "Improve code documentation",
                    "Implement code review standards"
                ],
                evidence={
                    "current_score": current['code_quality_score'],
                    "threshold": 60,
                    "findings": current.get('findings_count', 0)
                },
                generated_at=datetime.now()
            ))
        
        # Critical findings alert
        if current.get('critical_findings', 0) > 2:
            insights.append(Insight(
                id=f"critical_findings_alert_{repository}",
                title=f"Multiple Critical Findings Detected",
                description=f"{current['critical_findings']} critical issues require immediate attention",
                category="risk",
                severity="critical",
                confidence=0.99,
                affected_repositories=[repository],
                recommendations=[
                    "Address critical findings immediately",
                    "Create hotfix branches for critical issues",
                    "Notify team members",
                    "Schedule emergency review meeting"
                ],
                evidence={
                    "critical_findings": current['critical_findings'],
                    "total_findings": current.get('findings_count', 0)
                },
                generated_at=datetime.now()
            ))
        
        # Team sustainability risk
        if current.get('team_sustainability_score', 100) < 50:
            insights.append(Insight(
                id=f"team_risk_{repository}",
                title="Team Sustainability Issues Detected",
                description="Team sustainability score indicates potential knowledge gaps or capacity issues",
                category="risk",
                severity="medium",
                confidence=0.85,
                affected_repositories=[repository],
                recommendations=[
                    "Increase documentation",
                    "Improve knowledge sharing",
                    "Cross-train team members",
                    "Reduce individual dependencies"
                ],
                evidence={
                    "score": current.get('team_sustainability_score', 0),
                    "threshold": 50
                },
                generated_at=datetime.now()
            ))
        
        return insights
    
    def _identify_opportunity_insights(self, repository: str, current: Dict) -> List[Insight]:
        """Identify improvement opportunities"""
        insights = []
        
        # Strong performing area
        components = {
            'Security': current.get('security_score', 0),
            'Code Quality': current.get('code_quality_score', 0),
            'IP & Legal': current.get('ip_legal_score', 0),
            'Team Sustainability': current.get('team_sustainability_score', 0)
        }
        
        # Find strongest component
        if components:
            strongest = max(components.items(), key=lambda x: x[1])
            if strongest[1] > 80:
                insights.append(Insight(
                    id=f"strength_opportunity_{repository}",
                    title=f"Leverage {strongest[0]} Strengths",
                    description=f"Repository excels in {strongest[0]} (score: {strongest[1]}). Use as best practice model.",
                    category="opportunity",
                    severity="info",
                    confidence=0.9,
                    affected_repositories=[repository],
                    recommendations=[
                        f"Document {strongest[0]} best practices",
                        "Share practices with other teams",
                        "Consider mentoring other projects"
                    ],
                    evidence={
                        "component": strongest[0],
                        "score": strongest[1]
                    },
                    generated_at=datetime.now()
                ))
        
        # Improvement opportunity
        components_sorted = sorted(components.items(), key=lambda x: x[1])
        if components_sorted:
            weakest = components_sorted[0]
            if 50 < weakest[1] < 75:
                gap = 80 - weakest[1]
                insights.append(Insight(
                    id=f"improvement_opportunity_{repository}",
                    title=f"Quick Win: Improve {weakest[0]}",
                    description=f"{weakest[0]} is at {weakest[1]}. Small improvements can reach 80+",
                    category="opportunity",
                    severity="low",
                    confidence=0.8,
                    affected_repositories=[repository],
                    recommendations=[
                        f"Focus on {weakest[0]} improvements",
                        "Allocate 20% of sprint to this area",
                        "Track progress weekly"
                    ],
                    evidence={
                        "component": weakest[0],
                        "current_score": weakest[1],
                        "potential_gap": gap
                    },
                    generated_at=datetime.now()
                ))
        
        return insights
    
    def _identify_anomaly_insights(self, repository: str, current: Dict, history: List[Dict]) -> List[Insight]:
        """Identify anomalies in audit patterns"""
        insights = []
        
        if not history or len(history) < 2:
            return insights
        
        # Check for score drop
        previous = history[-1]
        current_score = current.get('overall_score', 0)
        previous_score = previous.get('overall_score', 0)
        score_drop = previous_score - current_score
        
        if score_drop > 10:
            insights.append(Insight(
                id=f"score_drop_anomaly_{repository}",
                title="Significant Score Drop Detected",
                description=f"Score dropped {score_drop:.1f} points from previous audit",
                category="anomaly",
                severity="high" if score_drop > 20 else "medium",
                confidence=0.95,
                affected_repositories=[repository],
                recommendations=[
                    "Investigate root cause of score drop",
                    "Review new findings",
                    "Check for recent code changes",
                    "Update audit expectations if needed"
                ],
                evidence={
                    "previous_score": previous_score,
                    "current_score": current_score,
                    "change": -score_drop
                },
                generated_at=datetime.now()
            ))
        
        # Check for finding spike
        current_findings = current.get('findings_count', 0)
        if history:
            avg_findings = statistics.mean([h.get('findings_count', 0) for h in history[-5:]])
            if current_findings > avg_findings * 1.5:
                insights.append(Insight(
                    id=f"findings_spike_{repository}",
                    title="Unusual Finding Spike",
                    description=f"Finding count increased to {current_findings} from average {avg_findings:.0f}",
                    category="anomaly",
                    severity="medium",
                    confidence=0.85,
                    affected_repositories=[repository],
                    recommendations=[
                        "Review newly introduced findings",
                        "Determine if findings are legitimate or false positives",
                        "Plan remediation for each finding"
                    ],
                    evidence={
                        "current_findings": current_findings,
                        "average_findings": round(avg_findings, 1),
                        "increase_percent": round((current_findings / avg_findings - 1) * 100, 1)
                    },
                    generated_at=datetime.now()
                ))
        
        return insights
    
    def _identify_trend_insights(self, repository: str, history: List[Dict]) -> List[Insight]:
        """Identify trend-based insights"""
        insights = []
        
        if not history or len(history) < 3:
            return insights
        
        recent_scores = [h.get('overall_score', 0) for h in history[-5:]]
        older_scores = [h.get('overall_score', 0) for h in history[-10:-5]]
        
        if older_scores:
            recent_avg = statistics.mean(recent_scores)
            older_avg = statistics.mean(older_scores)
            improvement = recent_avg - older_avg
            
            if improvement > 5:
                insights.append(Insight(
                    id=f"improving_trend_{repository}",
                    title="Positive Score Trend",
                    description=f"Repository shows consistent improvement ({improvement:.1f} points)",
                    category="trend",
                    severity="info",
                    confidence=0.9,
                    affected_repositories=[repository],
                    recommendations=[
                        "Continue current improvement efforts",
                        "Document what's working",
                        "Share practices with other teams"
                    ],
                    evidence={
                        "recent_average": round(recent_avg, 1),
                        "previous_average": round(older_avg, 1),
                        "improvement": round(improvement, 1)
                    },
                    generated_at=datetime.now()
                ))
            
            elif improvement < -5:
                insights.append(Insight(
                    id=f"declining_trend_{repository}",
                    title="Declining Score Trend",
                    description=f"Repository shows declining trend ({improvement:.1f} points)",
                    category="trend",
                    severity="high",
                    confidence=0.9,
                    affected_repositories=[repository],
                    recommendations=[
                        "Analyze root causes of decline",
                        "Implement improvement plan",
                        "Increase audit frequency to monitor"
                    ],
                    evidence={
                        "recent_average": round(recent_avg, 1),
                        "previous_average": round(older_avg, 1),
                        "decline": round(abs(improvement), 1)
                    },
                    generated_at=datetime.now()
                ))
        
        return insights
    
    def _identify_benchmark_insights(self, repository: str, current: Dict, peer_data: Dict) -> List[Insight]:
        """Identify benchmark comparison insights"""
        insights = []
        
        if not peer_data:
            return insights
        
        peer_scores = [p.get('overall_score', 0) for p in peer_data.values() if p]
        
        if not peer_scores:
            return insights
        
        current_score = current.get('overall_score', 0)
        peer_avg = statistics.mean(peer_scores)
        peer_median = statistics.median(peer_scores)
        
        if current_score > peer_avg + 10:
            insights.append(Insight(
                id=f"above_peers_{repository}",
                title="Outperforming Peers",
                description=f"Repository is {current_score - peer_avg:.0f} points above peer average",
                category="benchmark",
                severity="info",
                confidence=0.95,
                affected_repositories=[repository],
                recommendations=[
                    "Document success practices",
                    "Consider as mentor repository",
                    "Share findings in team sync"
                ],
                evidence={
                    "your_score": current_score,
                    "peer_average": round(peer_avg, 1),
                    "ahead_by": round(current_score - peer_avg, 1),
                    "peer_count": len(peer_data)
                },
                generated_at=datetime.now()
            ))
        
        elif current_score < peer_avg - 10:
            insights.append(Insight(
                id=f"below_peers_{repository}",
                title="Below Peer Performance",
                description=f"Repository is {peer_avg - current_score:.0f} points below peer average",
                category="benchmark",
                severity="medium",
                confidence=0.95,
                affected_repositories=[repository],
                recommendations=[
                    "Identify best practices from high-scoring peers",
                    "Create improvement plan",
                    "Request mentoring from peer teams"
                ],
                evidence={
                    "your_score": current_score,
                    "peer_average": round(peer_avg, 1),
                    "behind_by": round(peer_avg - current_score, 1),
                    "peer_count": len(peer_data)
                },
                generated_at=datetime.now()
            ))
        
        return insights
    
    def generate_report(self, insights: List[Insight], report_period_days: int = 30) -> InsightReport:
        """Generate comprehensive insight report"""
        
        # Count by severity and category
        by_severity = {}
        by_category = {}
        
        for insight in insights:
            by_severity[insight.severity] = by_severity.get(insight.severity, 0) + 1
            by_category[insight.category] = by_category.get(insight.category, 0) + 1
        
        # Generate executive summary
        summary_parts = []
        
        if by_severity.get('critical', 0) > 0:
            summary_parts.append(f"⚠️  {by_severity['critical']} critical issues require immediate action")
        
        if by_severity.get('high', 0) > 0:
            summary_parts.append(f"🔴 {by_severity['high']} high-priority items to address")
        
        if by_category.get('opportunity', 0) > 0:
            summary_parts.append(f"✨ {by_category['opportunity']} improvement opportunities identified")
        
        if by_category.get('trend', 0) > 0 and any(i.category == 'trend' and i.severity == 'info' for i in insights):
            summary_parts.append("📈 Positive trends detected in recent audits")
        
        executive_summary = "; ".join(summary_parts) if summary_parts else "✅ No significant issues detected"
        
        return InsightReport(
            generated_at=datetime.now(),
            report_period_days=report_period_days,
            total_insights=len(insights),
            by_severity=by_severity,
            by_category=by_category,
            insights=insights,
            executive_summary=executive_summary
        )
