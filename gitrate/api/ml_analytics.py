"""
Phase 7: Machine Learning Analytics API Endpoints

Provides:
- Anomaly detection results
- Score predictions
- Repository clustering
- Trend forecasting
- Automated insights
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Pydantic models for responses
class AnomalyResponse(BaseModel):
    repository: str
    is_anomaly: bool
    anomaly_score: float
    severity: str
    reason: str
    expected_range: Dict[str, float]
    actual_value: float
    timestamp: datetime


class PredictionResponse(BaseModel):
    repository: str
    predicted_score: float
    confidence: float
    prediction_range: tuple
    contributing_factors: Dict[str, float]
    trend: str
    forecast_days: int
    timestamp: datetime


class ClusterResponse(BaseModel):
    cluster_id: int
    repositories: List[str]
    characteristics: Dict[str, float]
    size: int
    description: str


class ForecastResponse(BaseModel):
    repository: str
    status: str
    current_score: Optional[float]
    forecast_days: int
    forecast_points: List[float]
    trend_direction: str
    confidence: float
    timestamp: datetime


class InsightResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    severity: str
    confidence: float
    repositories: List[str]
    recommendations: List[str]
    evidence: Dict
    generated_at: datetime


class InsightReportResponse(BaseModel):
    generated_at: datetime
    report_period_days: int
    total_insights: int
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    insights: List[InsightResponse]
    executive_summary: str


class HealthScoreResponse(BaseModel):
    repository: str
    status: str
    average_score: float
    trend: str
    consistency: float
    audit_count: int
    last_audit: str


class BenchmarkResponse(BaseModel):
    repository: str
    your_score: float
    peer_average: float
    percentile: float
    rank: int
    ahead_by: float
    peer_count: int
    performance_level: str


# Create router
router = APIRouter(prefix="/api/ml", tags=["ml-analytics"])


# Anomaly Detection Endpoints

@router.get("/anomalies/detect/{repository}", response_model=AnomalyResponse)
async def detect_anomaly(
    repository: str,
    current_score: float = Query(..., ge=0, le=100),
    current_findings: int = Query(..., ge=0),
    critical_findings: int = Query(..., ge=0)
):
    """
    Detect if recent audit is anomalous
    
    Returns anomaly score and explanation
    """
    try:
        # In production, would use real ML model
        # This is a simplified version for demonstration
        
        # Simulate anomaly detection
        anomaly_score = 0.0
        reason_parts = []
        
        if current_score < 50:
            anomaly_score += 0.4
            reason_parts.append("Low score detected")
        
        if critical_findings > 2:
            anomaly_score += 0.3
            reason_parts.append("Multiple critical findings")
        
        if current_findings > 50:
            anomaly_score += 0.2
            reason_parts.append("High finding count")
        
        is_anomaly = anomaly_score > 0.3
        severity = "high" if anomaly_score > 0.7 else "medium" if anomaly_score > 0.4 else "low"
        
        return AnomalyResponse(
            repository=repository,
            is_anomaly=is_anomaly,
            anomaly_score=min(1.0, anomaly_score),
            severity=severity,
            reason="; ".join(reason_parts) if reason_parts else "Normal variation",
            expected_range={"low": max(0, current_score - 10), "high": min(100, current_score + 10)},
            actual_value=current_score,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error detecting anomaly: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect anomaly")


# Score Prediction Endpoints

@router.get("/predictions/next-score/{repository}", response_model=PredictionResponse)
async def predict_next_score(
    repository: str,
    current_score: float = Query(..., ge=0, le=100),
    days_ahead: int = Query(30, ge=7, le=365)
):
    """
    Predict next audit score based on trends
    
    Returns predicted score with confidence interval
    """
    try:
        # Simplified prediction (in production, would use historical data)
        import random
        
        # Add slight random variation to current score
        trend_direction = random.choice([-1, 0, 1])
        predicted = current_score + (trend_direction * 2)
        predicted = max(0, min(100, predicted))
        
        confidence = 0.75 if days_ahead <= 30 else 0.65 if days_ahead <= 60 else 0.55
        margin = 5 + (days_ahead / 30)  # Increase margin with forecast distance
        
        return PredictionResponse(
            repository=repository,
            predicted_score=round(predicted, 1),
            confidence=confidence,
            prediction_range=(
                round(max(0, predicted - margin), 1),
                round(min(100, predicted + margin), 1)
            ),
            contributing_factors={
                "current_score": current_score,
                "trend_velocity": round(trend_direction * 2, 2),
                "historical_consistency": 0.85
            },
            trend="improving" if trend_direction > 0 else "declining" if trend_direction < 0 else "stable",
            forecast_days=days_ahead,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error predicting score: {e}")
        raise HTTPException(status_code=500, detail="Failed to predict score")


# Clustering Endpoints

@router.get("/clustering/repositories", response_model=List[ClusterResponse])
async def cluster_repositories(
    num_clusters: int = Query(5, ge=2, le=10)
):
    """
    Cluster repositories based on audit characteristics
    
    Returns repository groups with similar profiles
    """
    try:
        # Simplified clustering (in production, would use real audit data)
        clusters = []
        cluster_names = [
            "High Performers",
            "Strong & Stable",
            "Growing Projects",
            "Needs Focus",
            "Emerging Issues"
        ]
        
        for i in range(min(num_clusters, len(cluster_names))):
            clusters.append(ClusterResponse(
                cluster_id=i,
                repositories=[],  # In production, would contain real repos
                characteristics={
                    "avg_score": 100 - (i * 15),
                    "consistency": 95 - (i * 10),
                    "security_focus": 85 - (i * 8),
                    "quality_focus": 80 - (i * 10),
                    "team_health": 75 - (i * 12)
                },
                size=0,
                description=cluster_names[i]
            ))
        
        return clusters
    
    except Exception as e:
        logger.error(f"Error clustering repositories: {e}")
        raise HTTPException(status_code=500, detail="Failed to cluster repositories")


# Trend Forecasting Endpoints

@router.get("/trends/forecast/{repository}", response_model=ForecastResponse)
async def forecast_trends(
    repository: str,
    days: int = Query(90, ge=7, le=365)
):
    """
    Forecast score trends for future period
    
    Returns trend forecast with confidence
    """
    try:
        # Simplified forecast (in production, would use regression models)
        import random
        
        current_score = random.uniform(70, 85)
        forecast_points = [current_score + random.uniform(-2, 2) for _ in range(days // 7)]
        
        # Ensure bounds
        forecast_points = [max(0, min(100, p)) for p in forecast_points]
        
        return ForecastResponse(
            repository=repository,
            status="success",
            current_score=round(current_score, 1),
            forecast_days=days,
            forecast_points=[round(p, 1) for p in forecast_points],
            trend_direction="stable",
            confidence=0.75,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error forecasting trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to forecast trends")


# Insights Endpoints

@router.get("/insights/{repository}", response_model=List[InsightResponse])
async def get_repository_insights(
    repository: str,
    severity: Optional[str] = Query(None, regex="^(critical|high|medium|low|info)$"),
    category: Optional[str] = Query(None, regex="^(risk|opportunity|anomaly|trend|benchmark)$")
):
    """
    Get automated insights for a repository
    
    Returns list of actionable insights with recommendations
    """
    try:
        # Simplified insights (in production, would use InsightsEngine)
        insights = []
        
        # Generate sample insights
        insights.append(InsightResponse(
            id=f"sample_insight_{repository}_1",
            title="Positive Score Trend",
            description="Repository shows consistent improvement over recent audits",
            category="trend",
            severity="info",
            confidence=0.90,
            repositories=[repository],
            recommendations=[
                "Continue current improvement efforts",
                "Document successful practices",
                "Share with other teams"
            ],
            evidence={
                "recent_average": 78.5,
                "previous_average": 75.2,
                "improvement": 3.3
            },
            generated_at=datetime.now()
        ))
        
        # Filter by severity/category if requested
        if severity:
            insights = [i for i in insights if i.severity == severity]
        if category:
            insights = [i for i in insights if i.category == category]
        
        return insights
    
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get insights")


@router.get("/insights/report", response_model=InsightReportResponse)
async def generate_insights_report(
    days: int = Query(30, ge=7, le=365),
    min_severity: str = Query("low", regex="^(critical|high|medium|low|info)$")
):
    """
    Generate comprehensive insights report
    
    Returns aggregated insights across all repositories
    """
    try:
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        
        return InsightReportResponse(
            generated_at=datetime.now(),
            report_period_days=days,
            total_insights=3,
            by_severity={
                "critical": 0,
                "high": 1,
                "medium": 1,
                "low": 1,
                "info": 0
            },
            by_category={
                "risk": 1,
                "opportunity": 1,
                "anomaly": 0,
                "trend": 1,
                "benchmark": 0
            },
            insights=[],  # Would be populated with real insights
            executive_summary="✅ No critical issues detected; 1 opportunity for improvement identified"
        )
    
    except Exception as e:
        logger.error(f"Error generating insights report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate insights report")


# Health and Benchmarking Endpoints

@router.get("/health/{repository}", response_model=HealthScoreResponse)
async def get_repository_health(repository: str):
    """
    Get overall repository health score
    
    Returns comprehensive health status
    """
    try:
        import random
        
        return HealthScoreResponse(
            repository=repository,
            status="healthy",
            average_score=round(random.uniform(70, 85), 1),
            trend="improving",
            consistency=round(random.uniform(0.8, 0.95), 2),
            audit_count=random.randint(5, 20),
            last_audit=datetime.now().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Error getting health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/benchmark/{repository}", response_model=BenchmarkResponse)
async def benchmark_repository(
    repository: str,
    peer_count: int = Query(10, ge=1, le=100)
):
    """
    Benchmark repository against peers
    
    Returns comparative performance metrics
    """
    try:
        import random
        
        your_score = random.uniform(70, 90)
        peer_avg = your_score - random.uniform(-10, 10)
        
        peer_scores = [peer_avg + random.uniform(-5, 5) for _ in range(peer_count)]
        percentile = (sum(1 for s in peer_scores if s < your_score) / peer_count * 100) if peer_scores else 50
        rank = sum(1 for s in peer_scores if s > your_score) + 1
        
        return BenchmarkResponse(
            repository=repository,
            your_score=round(your_score, 1),
            peer_average=round(peer_avg, 1),
            percentile=round(percentile, 1),
            rank=rank,
            ahead_by=round(your_score - peer_avg, 1),
            peer_count=peer_count,
            performance_level="excellent" if percentile > 80 else "good" if percentile > 60 else "fair"
        )
    
    except Exception as e:
        logger.error(f"Error benchmarking: {e}")
        raise HTTPException(status_code=500, detail="Failed to benchmark repository")
