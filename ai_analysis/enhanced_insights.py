"""
Enhanced Insights Engine - Phase 7 Task 3

Advanced insight generation with:
- Expanded detection rules
- Persistence support
- Batch processing
- Risk scoring
- Actionable recommendations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class InsightSeverity(str, Enum):
    """Insight severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class InsightCategory(str, Enum):
    """Insight categories"""
    SECURITY = "security"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    TEAM = "team"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    ANOMALY = "anomaly"
    TREND = "trend"
    BENCHMARK = "benchmark"


@dataclass
class InsightEvidence:
    """Evidence supporting an insight"""
    metric_name: str
    metric_value: float
    threshold_value: float
    threshold_type: str  # "exceeds", "below", "spike", "drop"
    confidence: float
    data_points: int


@dataclass
class InsightRecommendation:
    """Actionable recommendation"""
    priority: str  # "high", "medium", "low"
    action: str
    expected_impact: str
    estimated_effort: str  # "quick", "medium", "significant"
    owner: str  # "team", "tech-lead", "security", "manager"


@dataclass
class EnhancedInsight:
    """Enhanced insight with metadata"""
    id: str
    title: str
    description: str
    category: InsightCategory
    severity: InsightSeverity
    confidence: float
    
    # Evidence
    evidence: List[InsightEvidence] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[InsightRecommendation] = field(default_factory=list)
    
    # Metadata
    affected_repositories: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    
    # Tracking
    impact_score: float = 0.0  # 0-100
    effort_score: float = 0.0  # 0-100 (higher = more effort)
    roi_score: float = 0.0  # Impact/Effort ratio
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class InsightBatch:
    """Batch of insights for processing"""
    batch_id: str
    generated_at: str
    insights: List[EnhancedInsight] = field(default_factory=list)
    
    # Summary statistics
    total_insights: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    by_category: Dict[str, int] = field(default_factory=dict)
    
    def add_insight(self, insight: EnhancedInsight):
        """Add insight to batch"""
        self.insights.append(insight)
        self.total_insights = len(self.insights)
        
        # Update counts
        if insight.severity == InsightSeverity.CRITICAL:
            self.critical_count += 1
        elif insight.severity == InsightSeverity.HIGH:
            self.high_count += 1
        elif insight.severity == InsightSeverity.MEDIUM:
            self.medium_count += 1
        elif insight.severity == InsightSeverity.LOW:
            self.low_count += 1
        
        # Update by category
        category_str = insight.category.value
        self.by_category[category_str] = self.by_category.get(category_str, 0) + 1
    
    def get_critical_insights(self) -> List[EnhancedInsight]:
        """Get critical insights only"""
        return [i for i in self.insights if i.severity == InsightSeverity.CRITICAL]
    
    def get_by_category(self, category: InsightCategory) -> List[EnhancedInsight]:
        """Get insights by category"""
        return [i for i in self.insights if i.category == category]
    
    def get_executive_summary(self) -> str:
        """Generate executive summary"""
        lines = [
            f"📊 Insight Batch Summary ({self.batch_id})",
            f"Generated: {self.generated_at}",
            f"Total Insights: {self.total_insights}",
            f"",
            f"Severity Distribution:",
            f"  🔴 Critical: {self.critical_count}",
            f"  🟠 High: {self.high_count}",
            f"  🟡 Medium: {self.medium_count}",
            f"  🔵 Low: {self.low_count}",
            f"",
            f"Top Categories:"
        ]
        
        for category, count in sorted(self.by_category.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"  • {category.title()}: {count}")
        
        # Add top action items
        high_priority_recommendations = []
        for insight in self.insights:
            for rec in insight.recommendations:
                if rec.priority == "high":
                    high_priority_recommendations.append(f"  • {rec.action} ({insight.title})")
        
        if high_priority_recommendations:
            lines.append(f"")
            lines.append(f"🎯 Top Action Items:")
            lines.extend(high_priority_recommendations[:5])
        
        return "\n".join(lines)


class EnhancedInsightsEngine:
    """Advanced insights generation engine"""
    
    def __init__(self):
        self.insight_cache: Dict[str, EnhancedInsight] = {}
        self.batch_history: List[InsightBatch] = []
        self.detector_enabled = {
            'security_risks': True,
            'quality_issues': True,
            'team_risks': True,
            'performance_anomalies': True,
            'regression_detection': True,
            'trend_changes': True,
            'peer_deviations': True,
            'unsustainable_patterns': True
        }
    
    def generate_enhanced_insights(
        self,
        repository: str,
        current_audit: Dict,
        historical_audits: List[Dict],
        peer_metrics: Dict
    ) -> List[EnhancedInsight]:
        """Generate comprehensive enhanced insights"""
        
        insights = []
        
        if self.detector_enabled['security_risks']:
            insights.extend(self._detect_security_risks(repository, current_audit, peer_metrics))
        
        if self.detector_enabled['quality_issues']:
            insights.extend(self._detect_quality_issues(repository, current_audit, peer_metrics))
        
        if self.detector_enabled['team_risks']:
            insights.extend(self._detect_team_risks(repository, current_audit, historical_audits))
        
        if self.detector_enabled['performance_anomalies']:
            insights.extend(self._detect_performance_anomalies(repository, current_audit, historical_audits))
        
        if self.detector_enabled['regression_detection']:
            insights.extend(self._detect_regression(repository, current_audit, historical_audits))
        
        if self.detector_enabled['trend_changes']:
            insights.extend(self._detect_trend_changes(repository, historical_audits))
        
        if self.detector_enabled['peer_deviations']:
            insights.extend(self._detect_peer_deviations(repository, current_audit, peer_metrics))
        
        if self.detector_enabled['unsustainable_patterns']:
            insights.extend(self._detect_unsustainable_patterns(repository, historical_audits))
        
        # Calculate impact and ROI scores
        for insight in insights:
            insight.impact_score = self._calculate_impact_score(insight)
            insight.effort_score = self._calculate_effort_score(insight)
            insight.roi_score = insight.impact_score / max(insight.effort_score, 1)
        
        return sorted(insights, key=lambda x: x.roi_score, reverse=True)
    
    def _detect_security_risks(
        self,
        repository: str,
        current_audit: Dict,
        peer_metrics: Dict
    ) -> List[EnhancedInsight]:
        """Detect security-related risks"""
        insights = []
        security_score = current_audit.get('security_score', 100)
        peer_security_avg = peer_metrics.get('avg_security_score', 80)
        
        # Critical security risk
        if security_score < 50:
            insights.append(EnhancedInsight(
                id=f"sec_risk_critical_{repository}",
                title="Critical Security Vulnerabilities Detected",
                description=f"Security score ({security_score}) is critically low. Immediate remediation required.",
                category=InsightCategory.SECURITY,
                severity=InsightSeverity.CRITICAL,
                confidence=0.98,
                evidence=[
                    InsightEvidence(
                        metric_name="security_score",
                        metric_value=security_score,
                        threshold_value=50,
                        threshold_type="below",
                        confidence=0.98,
                        data_points=1
                    )
                ],
                recommendations=[
                    InsightRecommendation(
                        priority="high",
                        action="Conduct immediate security audit",
                        expected_impact="Identify and fix critical vulnerabilities",
                        estimated_effort="significant",
                        owner="security"
                    ),
                    InsightRecommendation(
                        priority="high",
                        action="Review and update security policies",
                        expected_impact="Prevent future vulnerabilities",
                        estimated_effort="medium",
                        owner="security"
                    )
                ],
                affected_repositories=[repository]
            ))
        
        # High security risk
        elif security_score < 70:
            insights.append(EnhancedInsight(
                id=f"sec_risk_high_{repository}",
                title="Security Score Below Recommended Level",
                description=f"Security score ({security_score}) is below industry standard (80).",
                category=InsightCategory.SECURITY,
                severity=InsightSeverity.HIGH,
                confidence=0.95,
                evidence=[
                    InsightEvidence(
                        metric_name="security_score",
                        metric_value=security_score,
                        threshold_value=70,
                        threshold_type="below",
                        confidence=0.95,
                        data_points=1
                    )
                ],
                recommendations=[
                    InsightRecommendation(
                        priority="high",
                        action="Schedule security review",
                        expected_impact="Identify security gaps",
                        estimated_effort="medium",
                        owner="security"
                    )
                ],
                affected_repositories=[repository]
            ))
        
        # Peer comparison
        if peer_security_avg > 0 and security_score < peer_security_avg - 15:
            insights.append(EnhancedInsight(
                id=f"sec_peer_gap_{repository}",
                title="Significant Security Gap vs Peers",
                description=f"Security score is {peer_security_avg - security_score:.0f} points below peer average.",
                category=InsightCategory.SECURITY,
                severity=InsightSeverity.MEDIUM,
                confidence=0.90,
                evidence=[
                    InsightEvidence(
                        metric_name="security_vs_peers",
                        metric_value=security_score,
                        threshold_value=peer_security_avg - 15,
                        threshold_type="below",
                        confidence=0.90,
                        data_points=1
                    )
                ],
                recommendations=[
                    InsightRecommendation(
                        priority="medium",
                        action="Benchmark against high-scoring peers",
                        expected_impact="Identify best practices",
                        estimated_effort="quick",
                        owner="tech-lead"
                    )
                ],
                affected_repositories=[repository]
            ))
        
        return insights
    
    def _detect_quality_issues(
        self,
        repository: str,
        current_audit: Dict,
        peer_metrics: Dict
    ) -> List[EnhancedInsight]:
        """Detect code quality issues"""
        insights = []
        quality_score = current_audit.get('code_quality_score', 100)
        findings_count = current_audit.get('findings_count', 0)
        
        if quality_score < 60:
            insights.append(EnhancedInsight(
                id=f"qual_critical_{repository}",
                title="Critical Code Quality Issues",
                description=f"Code quality score is {quality_score}. {findings_count} findings identified.",
                category=InsightCategory.QUALITY,
                severity=InsightSeverity.CRITICAL,
                confidence=0.97,
                evidence=[
                    InsightEvidence(
                        metric_name="code_quality_score",
                        metric_value=quality_score,
                        threshold_value=60,
                        threshold_type="below",
                        confidence=0.97,
                        data_points=1
                    ),
                    InsightEvidence(
                        metric_name="findings_count",
                        metric_value=findings_count,
                        threshold_value=50,
                        threshold_type="exceeds",
                        confidence=0.95,
                        data_points=1
                    )
                ],
                recommendations=[
                    InsightRecommendation(
                        priority="high",
                        action="Create code quality improvement plan",
                        expected_impact="Reduce findings by 50%+",
                        estimated_effort="significant",
                        owner="tech-lead"
                    ),
                    InsightRecommendation(
                        priority="high",
                        action="Enable automated code analysis in CI/CD",
                        expected_impact="Catch issues earlier",
                        estimated_effort="medium",
                        owner="tech-lead"
                    )
                ],
                affected_repositories=[repository]
            ))
        
        elif quality_score < 75:
            insights.append(EnhancedInsight(
                id=f"qual_high_{repository}",
                title="Code Quality Below Standards",
                description=f"Code quality score is {quality_score}.",
                category=InsightCategory.QUALITY,
                severity=InsightSeverity.HIGH,
                confidence=0.94,
                evidence=[
                    InsightEvidence(
                        metric_name="code_quality_score",
                        metric_value=quality_score,
                        threshold_value=75,
                        threshold_type="below",
                        confidence=0.94,
                        data_points=1
                    )
                ],
                recommendations=[
                    InsightRecommendation(
                        priority="medium",
                        action="Schedule code review session",
                        expected_impact="Identify improvement areas",
                        estimated_effort="quick",
                        owner="tech-lead"
                    )
                ],
                affected_repositories=[repository]
            ))
        
        return insights
    
    def _detect_team_risks(
        self,
        repository: str,
        current_audit: Dict,
        historical_audits: List[Dict]
    ) -> List[EnhancedInsight]:
        """Detect team sustainability and capacity risks"""
        insights = []
        team_score = current_audit.get('team_sustainability_score', 100)
        
        if team_score < 50:
            insights.append(EnhancedInsight(
                id=f"team_risk_critical_{repository}",
                title="Critical Team Sustainability Risk",
                description=f"Team sustainability score is {team_score}. Risk of staff turnover or burnout.",
                category=InsightCategory.TEAM,
                severity=InsightSeverity.CRITICAL,
                confidence=0.92,
                evidence=[
                    InsightEvidence(
                        metric_name="team_sustainability_score",
                        metric_value=team_score,
                        threshold_value=50,
                        threshold_type="below",
                        confidence=0.92,
                        data_points=1
                    )
                ],
                recommendations=[
                    InsightRecommendation(
                        priority="high",
                        action="Meet with team to assess workload",
                        expected_impact="Prevent burnout and turnover",
                        estimated_effort="quick",
                        owner="manager"
                    ),
                    InsightRecommendation(
                        priority="high",
                        action="Reduce work complexity or add resources",
                        expected_impact="Improve team health",
                        estimated_effort="significant",
                        owner="manager"
                    )
                ],
                affected_repositories=[repository]
            ))
        
        return insights
    
    def _detect_performance_anomalies(
        self,
        repository: str,
        current_audit: Dict,
        historical_audits: List[Dict]
    ) -> List[EnhancedInsight]:
        """Detect unexpected performance changes"""
        insights = []
        
        if len(historical_audits) >= 3:
            current_score = current_audit.get('overall_score', 0)
            recent_scores = [a.get('overall_score', 0) for a in historical_audits[-3:]]
            
            if recent_scores:
                avg_recent = sum(recent_scores) / len(recent_scores)
                drop = avg_recent - current_score
                
                if drop > 15:
                    insights.append(EnhancedInsight(
                        id=f"perf_anomaly_{repository}",
                        title="Significant Performance Drop Detected",
                        description=f"Overall score dropped {drop:.1f} points ({current_score:.0f} vs {avg_recent:.0f} average).",
                        category=InsightCategory.PERFORMANCE,
                        severity=InsightSeverity.HIGH if drop > 20 else InsightSeverity.MEDIUM,
                        confidence=0.93,
                        evidence=[
                            InsightEvidence(
                                metric_name="score_drop",
                                metric_value=current_score,
                                threshold_value=avg_recent - 15,
                                threshold_type="drop",
                                confidence=0.93,
                                data_points=len(historical_audits)
                            )
                        ],
                        recommendations=[
                            InsightRecommendation(
                                priority="high",
                                action="Investigate recent changes",
                                expected_impact="Identify root cause",
                                estimated_effort="quick",
                                owner="tech-lead"
                            ),
                            InsightRecommendation(
                                priority="high",
                                action="Create action plan to recover",
                                expected_impact="Return to baseline within 2 weeks",
                                estimated_effort="medium",
                                owner="tech-lead"
                            )
                        ],
                        affected_repositories=[repository]
                    ))
        
        return insights
    
    def _detect_regression(
        self,
        repository: str,
        current_audit: Dict,
        historical_audits: List[Dict]
    ) -> List[EnhancedInsight]:
        """Detect score regression trends"""
        return []  # Placeholder for regression detection
    
    def _detect_trend_changes(
        self,
        repository: str,
        historical_audits: List[Dict]
    ) -> List[EnhancedInsight]:
        """Detect changes in score trends"""
        return []  # Placeholder for trend change detection
    
    def _detect_peer_deviations(
        self,
        repository: str,
        current_audit: Dict,
        peer_metrics: Dict
    ) -> List[EnhancedInsight]:
        """Detect significant deviations from peer averages"""
        return []  # Placeholder for peer deviation detection
    
    def _detect_unsustainable_patterns(
        self,
        repository: str,
        historical_audits: List[Dict]
    ) -> List[EnhancedInsight]:
        """Detect unsustainable patterns in audit data"""
        return []  # Placeholder for pattern detection
    
    def _calculate_impact_score(self, insight: EnhancedInsight) -> float:
        """Calculate impact score 0-100"""
        severity_weight = {
            InsightSeverity.CRITICAL: 100,
            InsightSeverity.HIGH: 80,
            InsightSeverity.MEDIUM: 60,
            InsightSeverity.LOW: 40,
            InsightSeverity.INFO: 20
        }
        
        base = severity_weight.get(insight.severity, 50)
        return base * insight.confidence
    
    def _calculate_effort_score(self, insight: EnhancedInsight) -> float:
        """Calculate effort score 0-100"""
        effort_weights = {
            'quick': 20,
            'medium': 50,
            'significant': 80
        }
        
        if not insight.recommendations:
            return 50
        
        # Average effort across recommendations
        efforts = [
            effort_weights.get(rec.estimated_effort, 50)
            for rec in insight.recommendations
        ]
        
        return sum(efforts) / len(efforts) if efforts else 50
    
    def generate_batch(
        self,
        batch_id: str,
        repositories: Dict[str, Dict]
    ) -> InsightBatch:
        """Generate batch of insights for multiple repositories"""
        batch = InsightBatch(
            batch_id=batch_id,
            generated_at=datetime.now().isoformat()
        )
        
        for repo_name, repo_data in repositories.items():
            insights = self.generate_enhanced_insights(
                repository=repo_name,
                current_audit=repo_data.get('current', {}),
                historical_audits=repo_data.get('history', []),
                peer_metrics=repo_data.get('peers', {})
            )
            
            for insight in insights:
                batch.add_insight(insight)
        
        self.batch_history.append(batch)
        return batch
    
    def get_batch_summary(self, batch_id: str) -> Optional[str]:
        """Get summary for a batch"""
        for batch in self.batch_history:
            if batch.batch_id == batch_id:
                return batch.get_executive_summary()
        
        return None
    
    def enable_detectors(self, detectors: Dict[str, bool]):
        """Enable/disable specific detectors"""
        self.detector_enabled.update(detectors)
        logger.info(f"Detectors updated: {detectors}")
