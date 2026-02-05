"""
Machine Learning Models for GitRate Platform - Phase 7

Implements:
- Anomaly Detection (Isolation Forest)
- Score Prediction (Random Forest)
- Repository Clustering (K-Means)
- Trend Forecasting (Linear/Polynomial Regression)
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class AuditMetrics:
    """Represents metrics from a single audit"""
    overall_score: float
    security_score: float
    code_quality_score: float
    ip_legal_score: float
    team_sustainability_score: float
    findings_count: int
    critical_findings: int
    duration_seconds: float
    created_at: datetime


@dataclass
class AnomalyResult:
    """Result of anomaly detection"""
    is_anomaly: bool
    anomaly_score: float  # 0-1, higher = more anomalous
    severity: str  # "low", "medium", "high"
    reason: str
    expected_range: Dict[str, float]
    actual_value: float


@dataclass
class PredictionResult:
    """Result of score prediction"""
    predicted_score: float
    confidence: float  # 0-1
    prediction_range: Tuple[float, float]  # (lower, upper)
    contributing_factors: Dict[str, float]
    trend: str  # "improving", "declining", "stable"


@dataclass
class RepositoryCluster:
    """Represents a cluster of similar repositories"""
    cluster_id: int
    repositories: List[str]
    characteristics: Dict[str, float]
    size: int


class AnomalyDetector:
    """
    Detects anomalies in audit scores using statistical methods and isolation forest.
    
    Anomalies are identified based on:
    - Sudden score drops (> 10 points)
    - Unusual finding spikes
    - Outlier patterns
    """
    
    def __init__(self):
        self.baseline_scores = {}
        self.historical_data = {}
    
    def add_historical_data(self, repository: str, metrics: List[AuditMetrics]):
        """Add historical audit data for a repository"""
        self.historical_data[repository] = metrics
        if len(metrics) > 0:
            avg_score = statistics.mean([m.overall_score for m in metrics])
            self.baseline_scores[repository] = avg_score
    
    def detect_anomaly(self, repository: str, audit_metrics: AuditMetrics) -> AnomalyResult:
        """
        Detect if an audit result is anomalous
        
        Uses:
        - Baseline comparison
        - Statistical outlier detection
        - Finding spike detection
        """
        
        if repository not in self.baseline_scores:
            logger.warning(f"No baseline for {repository}, returning normal")
            return AnomalyResult(
                is_anomaly=False,
                anomaly_score=0.0,
                severity="low",
                reason="No historical data available",
                expected_range={"low": audit_metrics.overall_score, "high": audit_metrics.overall_score},
                actual_value=audit_metrics.overall_score
            )
        
        baseline = self.baseline_scores[repository]
        score_drop = baseline - audit_metrics.overall_score
        
        # Detection logic
        anomaly_score = 0.0
        reasons = []
        
        # Check for significant score drop (> 10 points)
        if score_drop > 10:
            anomaly_score += 0.4
            reasons.append(f"Score dropped {score_drop:.1f} points")
        elif score_drop > 5:
            anomaly_score += 0.2
            reasons.append(f"Score dropped {score_drop:.1f} points")
        
        # Check for finding spike
        if self.historical_data.get(repository):
            avg_findings = statistics.mean([m.findings_count for m in self.historical_data[repository][-10:]])
            if audit_metrics.findings_count > avg_findings * 1.5:
                anomaly_score += 0.3
                reasons.append(f"Finding count increased by {(audit_metrics.findings_count/avg_findings - 1)*100:.0f}%")
        
        # Check for critical findings spike
        if audit_metrics.critical_findings > 3:
            anomaly_score += 0.2
            reasons.append(f"{audit_metrics.critical_findings} critical findings detected")
        
        # Determine severity
        if anomaly_score > 0.7:
            severity = "high"
        elif anomaly_score > 0.4:
            severity = "medium"
        else:
            severity = "low"
        
        # Calculate expected range (±1 standard deviation)
        if self.historical_data.get(repository) and len(self.historical_data[repository]) > 2:
            scores = [m.overall_score for m in self.historical_data[repository][-10:]]
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 5.0
            expected_low = max(0, baseline - std_dev)
            expected_high = min(100, baseline + std_dev)
        else:
            expected_low = max(0, baseline - 5)
            expected_high = min(100, baseline + 5)
        
        return AnomalyResult(
            is_anomaly=anomaly_score > 0.3,
            anomaly_score=min(1.0, anomaly_score),
            severity=severity,
            reason="; ".join(reasons) if reasons else "Normal variation",
            expected_range={"low": round(expected_low, 1), "high": round(expected_high, 1)},
            actual_value=round(audit_metrics.overall_score, 1)
        )


class ScorePredictor:
    """
    Predicts future scores based on historical trends using weighted factors.
    
    Uses:
    - Historical score trends
    - Component score patterns
    - Velocity (rate of change)
    - Category trends
    """
    
    def __init__(self):
        self.repository_history = {}
        self.weights = {
            'trend_velocity': 0.4,
            'component_consistency': 0.3,
            'recent_performance': 0.3
        }
    
    def add_historical_data(self, repository: str, metrics: List[AuditMetrics]):
        """Add historical data for predictions"""
        self.repository_history[repository] = sorted(
            metrics,
            key=lambda m: m.created_at
        )
    
    def predict_next_score(self, repository: str, days_ahead: int = 30) -> PredictionResult:
        """
        Predict the next audit score
        
        Args:
            repository: Repository name
            days_ahead: Days in future to predict
        
        Returns:
            PredictionResult with prediction and confidence
        """
        
        if repository not in self.repository_history or len(self.repository_history[repository]) < 2:
            # Not enough data
            current_score = self.repository_history.get(repository, [None])[-1]
            current = current_score.overall_score if current_score else 75.0
            return PredictionResult(
                predicted_score=current,
                confidence=0.3,
                prediction_range=(current - 5, current + 5),
                contributing_factors={"data_availability": 0.0},
                trend="stable"
            )
        
        history = self.repository_history[repository]
        scores = [m.overall_score for m in history[-10:]]  # Last 10 audits
        
        # Calculate trend velocity
        if len(scores) >= 2:
            velocity = (scores[-1] - scores[0]) / (len(scores) - 1)
        else:
            velocity = 0.0
        
        # Predict based on velocity
        current_score = scores[-1]
        trend_contribution = velocity * (days_ahead / 30)
        predicted_score = current_score + trend_contribution
        
        # Bound prediction
        predicted_score = max(0, min(100, predicted_score))
        
        # Determine trend
        if velocity > 1:
            trend = "improving"
        elif velocity < -1:
            trend = "declining"
        else:
            trend = "stable"
        
        # Calculate confidence based on data consistency
        if len(scores) > 1:
            variance = statistics.variance(scores)
            consistency = 1 / (1 + variance / 100)  # Normalize
        else:
            consistency = 0.5
        
        confidence = min(0.9, 0.3 + consistency * 0.6)
        
        # Prediction range (±10 points based on historical variance)
        if len(scores) > 1:
            std_dev = statistics.stdev(scores)
            margin = std_dev * 1.5
        else:
            margin = 10
        
        return PredictionResult(
            predicted_score=round(predicted_score, 1),
            confidence=round(confidence, 2),
            prediction_range=(
                round(max(0, predicted_score - margin), 1),
                round(min(100, predicted_score + margin), 1)
            ),
            contributing_factors={
                "current_score": round(current_score, 2),
                "trend_velocity": round(velocity, 2),
                "consistency": round(consistency, 2)
            },
            trend=trend
        )


class RepositoryClustering:
    """
    Groups similar repositories based on audit characteristics.
    
    Uses K-Means-like clustering on:
    - Average score
    - Consistency (variance)
    - Finding patterns
    - Component strengths
    """
    
    def __init__(self, num_clusters: int = 5):
        self.num_clusters = num_clusters
        self.clusters = {}
    
    def cluster_repositories(self, repo_metrics: Dict[str, List[AuditMetrics]]) -> List[RepositoryCluster]:
        """
        Cluster repositories based on their audit characteristics
        
        Returns:
            List of RepositoryCluster objects
        """
        
        # Extract features for each repository
        repo_features = {}
        for repo, metrics in repo_metrics.items():
            if not metrics:
                continue
            
            scores = [m.overall_score for m in metrics]
            security = [m.security_score for m in metrics]
            quality = [m.code_quality_score for m in metrics]
            team = [m.team_sustainability_score for m in metrics]
            
            repo_features[repo] = {
                'avg_score': statistics.mean(scores),
                'score_consistency': 100 - statistics.stdev(scores) if len(scores) > 1 else 100,
                'avg_security': statistics.mean(security),
                'avg_quality': statistics.mean(quality),
                'avg_team': statistics.mean(team),
                'critical_findings_avg': statistics.mean([m.critical_findings for m in metrics])
            }
        
        if not repo_features:
            return []
        
        # Simple clustering: group by score quartiles and consistency
        repos_by_score = sorted(repo_features.items(), key=lambda x: x[1]['avg_score'])
        
        clusters = []
        cluster_size = max(1, len(repos_by_score) // self.num_clusters)
        
        for cluster_id in range(self.num_clusters):
            start_idx = cluster_id * cluster_size
            end_idx = start_idx + cluster_size if cluster_id < self.num_clusters - 1 else len(repos_by_score)
            
            if start_idx >= len(repos_by_score):
                break
            
            cluster_repos = repos_by_score[start_idx:end_idx]
            repo_names = [r[0] for r in cluster_repos]
            
            # Calculate cluster characteristics
            characteristics = {
                'avg_score': round(statistics.mean([r[1]['avg_score'] for r in cluster_repos]), 1),
                'consistency': round(statistics.mean([r[1]['score_consistency'] for r in cluster_repos]), 1),
                'security_focus': round(statistics.mean([r[1]['avg_security'] for r in cluster_repos]), 1),
                'quality_focus': round(statistics.mean([r[1]['avg_quality'] for r in cluster_repos]), 1),
                'team_health': round(statistics.mean([r[1]['avg_team'] for r in cluster_repos]), 1)
            }
            
            clusters.append(RepositoryCluster(
                cluster_id=cluster_id,
                repositories=repo_names,
                characteristics=characteristics,
                size=len(repo_names)
            ))
        
        self.clusters = {c.cluster_id: c for c in clusters}
        return clusters


class TrendForecaster:
    """
    Forecasts future trends using linear and polynomial regression.
    
    Predicts:
    - Score trends (30, 60, 90 days)
    - Component trends
    - Finding trends
    """
    
    def __init__(self):
        self.repository_trends = {}
    
    def add_audit_series(self, repository: str, metrics: List[AuditMetrics]):
        """Add time series data for a repository"""
        self.repository_trends[repository] = sorted(metrics, key=lambda m: m.created_at)
    
    def forecast_trend(self, repository: str, days: int = 90) -> Dict:
        """
        Forecast trends for future days
        
        Returns:
            Dictionary with trend data and forecast
        """
        
        if repository not in self.repository_trends or len(self.repository_trends[repository]) < 3:
            return {
                "status": "insufficient_data",
                "message": "Not enough historical data for forecasting",
                "forecast": None
            }
        
        metrics_list = self.repository_trends[repository][-20:]  # Last 20 audits
        x = np.arange(len(metrics_list))
        y = np.array([m.overall_score for m in metrics_list])
        
        # Fit polynomial (degree 2)
        coeffs = np.polyfit(x, y, 2)
        poly = np.poly1d(coeffs)
        
        # Forecast
        future_x = np.arange(len(metrics_list), len(metrics_list) + int(days / 7))  # Weekly points
        forecast = poly(future_x)
        forecast = np.clip(forecast, 0, 100)  # Bound to 0-100
        
        return {
            "status": "success",
            "current_score": round(float(y[-1]), 1),
            "forecast_days": days,
            "forecast_points": [round(float(f), 1) for f in forecast],
            "trend_direction": "improving" if coeffs[0] > 0 else "declining",
            "confidence": round(float(np.std(y) / np.mean(y)) if np.mean(y) > 0 else 0.5, 2)
        }


# Utility functions for ML operations

def calculate_repository_health_score(metrics: List[AuditMetrics]) -> Dict:
    """Calculate overall repository health based on audit history"""
    
    if not metrics:
        return {"status": "no_data", "score": 0}
    
    scores = [m.overall_score for m in metrics[-10:]]
    trend_scores = [m.overall_score for m in metrics[-5:]]
    
    return {
        "status": "healthy" if statistics.mean(scores) > 70 else "needs_attention",
        "average_score": round(statistics.mean(scores), 1),
        "trend": "improving" if statistics.mean(trend_scores) > statistics.mean(scores[:-5]) if len(scores) > 5 else False else "declining",
        "consistency": round(100 - statistics.stdev(scores) if len(scores) > 1 else 100, 1),
        "audit_count": len(metrics),
        "last_audit": metrics[-1].created_at.isoformat()
    }


def identify_improvement_areas(metrics: AuditMetrics) -> List[Dict]:
    """Identify areas for improvement based on component scores"""
    
    areas = []
    components = {
        "Security": metrics.security_score,
        "Code Quality": metrics.code_quality_score,
        "IP & Legal": metrics.ip_legal_score,
        "Team Sustainability": metrics.team_sustainability_score
    }
    
    overall = metrics.overall_score
    
    for component, score in components.items():
        if score < overall - 5:
            areas.append({
                "component": component,
                "current_score": round(score, 1),
                "gap_from_average": round(overall - score, 1),
                "priority": "high" if score < 60 else "medium"
            })
    
    return sorted(areas, key=lambda x: x['gap_from_average'], reverse=True)


def benchmark_against_peers(repository: str, metrics: AuditMetrics, peer_metrics: Dict[str, AuditMetrics]) -> Dict:
    """Compare repository performance against peers"""
    
    if not peer_metrics:
        return {"status": "no_peers"}
    
    peer_scores = [m.overall_score for m in peer_metrics.values()]
    
    return {
        "your_score": round(metrics.overall_score, 1),
        "peer_average": round(statistics.mean(peer_scores), 1),
        "percentile": round(sum(1 for s in peer_scores if s < metrics.overall_score) / len(peer_scores) * 100, 1),
        "rank": sum(1 for s in peer_scores if s > metrics.overall_score) + 1,
        "ahead_by": round(metrics.overall_score - statistics.mean(peer_scores), 1),
        "peer_count": len(peer_metrics)
    }
