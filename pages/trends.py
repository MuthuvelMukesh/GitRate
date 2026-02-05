"""Trend analysis and historical audit data visualization."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from statistics import mean, stdev

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trends", tags=["Trends"])


# ===== RESPONSE MODELS =====

class TrendPoint(BaseModel):
    """Single data point in trend."""
    date: str
    value: float
    count: int


class RepositoryTrendResponse(BaseModel):
    """Trend data for single repository."""
    repository: str
    trend: List[TrendPoint]
    average: float
    trend_direction: str  # "improving", "declining", "stable"
    forecast_next_audit: Optional[float] = None


class MetricTrendResponse(BaseModel):
    """Trend for metric across all repositories."""
    metric: str
    trend: List[TrendPoint]
    average: float
    std_dev: float
    best_value: float
    worst_value: float


# ===== ENDPOINTS =====

@router.get("/repository/{repository}", response_model=RepositoryTrendResponse)
async def get_repository_trend(
    repository: str,
    days: int = Query(90, ge=7, le=365),
) -> RepositoryTrendResponse:
    """
    Get audit score trend for specific repository.
    
    Args:
        repository: Repository name
        days: Number of days to analyze
    
    Returns:
        Trend data with forecasting
    """
    try:
        async with AsyncSessionLocal() as session:
            # Get audits for repository in date range
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                f"""
                SELECT DATE(created_at) as date, overall_score, COUNT(*) as count
                FROM audits
                WHERE repository = %s AND created_at > %s
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at)
                """,
                (repository, cutoff)
            )
            
            audits = result.fetchall()
            
            if not audits:
                raise HTTPException(
                    status_code=404,
                    detail=f"No audits found for repository {repository}"
                )
            
            # Build trend
            trend_points = [
                TrendPoint(
                    date=str(audit[0]),
                    value=float(audit[1]),
                    count=audit[2]
                )
                for audit in audits
            ]
            
            # Calculate statistics
            scores = [float(audit[1]) for audit in audits]
            average = mean(scores)
            
            # Determine trend direction
            if len(scores) >= 2:
                recent_avg = mean(scores[-5:]) if len(scores) >= 5 else scores[-1]
                old_avg = mean(scores[:5]) if len(scores) >= 5 else scores[0]
                
                if recent_avg > old_avg + 5:
                    trend_direction = "improving"
                elif recent_avg < old_avg - 5:
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"
            
            # Simple linear regression forecast
            forecast = None
            if len(scores) >= 3:
                n = len(scores)
                x_values = list(range(n))
                y_values = scores
                
                x_mean = mean(x_values)
                y_mean = mean(y_values)
                
                numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
                denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
                
                if denominator != 0:
                    slope = numerator / denominator
                    intercept = y_mean - slope * x_mean
                    forecast = max(0, min(100, slope * n + intercept))
            
            logger.info(f"Trend analysis for {repository}: {trend_direction}")
            
            return RepositoryTrendResponse(
                repository=repository,
                trend=trend_points,
                average=average,
                trend_direction=trend_direction,
                forecast_next_audit=forecast,
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing repository trend: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metric/{metric}", response_model=MetricTrendResponse)
async def get_metric_trend(
    metric: str = Query(..., description="Metric: overall, security, code_quality, ip_legal, team_sustainability"),
    days: int = Query(90, ge=7, le=365),
) -> MetricTrendResponse:
    """
    Get trend for metric across all repositories.
    
    Args:
        metric: Metric name
        days: Number of days to analyze
    
    Returns:
        Trend data across all repos
    """
    try:
        metric_map = {
            "overall": "overall_score",
            "security": "security_score",
            "code_quality": "code_quality_score",
            "ip_legal": "ip_legal_score",
            "team_sustainability": "team_sustainability_score",
        }
        
        if metric not in metric_map:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown metric: {metric}"
            )
        
        score_column = metric_map[metric]
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                f"""
                SELECT DATE(created_at) as date, AVG({score_column}), COUNT(*)
                FROM audits
                WHERE created_at > %s
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at)
                """,
                (cutoff,)
            )
            
            audits = result.fetchall()
            
            if not audits:
                raise HTTPException(
                    status_code=404,
                    detail="No audit data found"
                )
            
            # Build trend
            trend_points = [
                TrendPoint(
                    date=str(audit[0]),
                    value=float(audit[1]),
                    count=audit[2]
                )
                for audit in audits
            ]
            
            # Calculate statistics
            scores = [float(audit[1]) for audit in audits]
            average = mean(scores)
            std_dev = stdev(scores) if len(scores) > 1 else 0
            
            logger.info(f"Trend analysis for metric {metric}: avg={average:.1f}")
            
            return MetricTrendResponse(
                metric=metric,
                trend=trend_points,
                average=average,
                std_dev=std_dev,
                best_value=max(scores),
                worst_value=min(scores),
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing metric trend: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison/{repo1}/{repo2}")
async def compare_repository_trends(
    repo1: str,
    repo2: str,
    days: int = Query(90, ge=7, le=365),
) -> Dict[str, Any]:
    """
    Compare trends between two repositories.
    
    Args:
        repo1: First repository
        repo2: Second repository
        days: Number of days to analyze
    
    Returns:
        Comparison with insights
    """
    try:
        async with AsyncSessionLocal() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Get repo1 data
            result1 = await session.execute(
                """
                SELECT overall_score, created_at
                FROM audits
                WHERE repository = %s AND created_at > %s
                ORDER BY created_at
                """,
                (repo1, cutoff)
            )
            repo1_data = result1.fetchall()
            
            # Get repo2 data
            result2 = await session.execute(
                """
                SELECT overall_score, created_at
                FROM audits
                WHERE repository = %s AND created_at > %s
                ORDER BY created_at
                """,
                (repo2, cutoff)
            )
            repo2_data = result2.fetchall()
            
            if not repo1_data or not repo2_data:
                raise HTTPException(
                    status_code=404,
                    detail="One or both repositories have no audit data"
                )
            
            # Calculate statistics
            scores1 = [float(d[0]) for d in repo1_data]
            scores2 = [float(d[0]) for d in repo2_data]
            
            avg1 = mean(scores1)
            avg2 = mean(scores2)
            
            # Generate insights
            insights = []
            
            if avg1 > avg2:
                insights.append(f"{repo1} has better average score ({avg1:.1f} vs {avg2:.1f})")
            else:
                insights.append(f"{repo2} has better average score ({avg2:.1f} vs {avg1:.1f})")
            
            # Check stability
            std1 = stdev(scores1) if len(scores1) > 1 else 0
            std2 = stdev(scores2) if len(scores2) > 1 else 0
            
            if std1 < std2:
                insights.append(f"{repo1} has more consistent scores")
            else:
                insights.append(f"{repo2} has more consistent scores")
            
            logger.info(f"Compared trends for {repo1} and {repo2}")
            
            return {
                "repo1": {
                    "name": repo1,
                    "average_score": avg1,
                    "audit_count": len(scores1),
                    "std_dev": std1,
                    "latest_score": scores1[-1] if scores1 else None,
                },
                "repo2": {
                    "name": repo2,
                    "average_score": avg2,
                    "audit_count": len(scores2),
                    "std_dev": std2,
                    "latest_score": scores2[-1] if scores2 else None,
                },
                "insights": insights,
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing repository trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-check")
async def get_audit_health_check() -> Dict[str, Any]:
    """
    Get overall audit health metrics.
    
    Returns:
        Health check with recommendations
    """
    try:
        async with AsyncSessionLocal() as session:
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            # Recent audits
            result = await session.execute(
                f"SELECT COUNT(*) FROM audits WHERE created_at > '{week_ago}'"
            )
            recent_count = result.scalar() or 0
            
            # Critical findings trend
            result = await session.execute(
                f"SELECT COUNT(*) FROM findings WHERE severity = 'CRITICAL' AND created_at > '{week_ago}'"
            )
            critical_count = result.scalar() or 0
            
            # Average score trend
            result = await session.execute(
                f"SELECT AVG(overall_score) FROM audits WHERE created_at > '{week_ago}'"
            )
            avg_score = result.scalar() or 0
            
            recommendations = []
            
            if critical_count > recent_count * 0.5:
                recommendations.append("High critical finding rate - prioritize security issues")
            
            if avg_score < 50:
                recommendations.append("Low average scores - consider comprehensive code review")
            
            if recent_count < 5:
                recommendations.append("Low audit frequency - increase monitoring")
            
            logger.info("Audit health check completed")
            
            return {
                "status": "healthy" if avg_score > 60 and critical_count < recent_count else "warning",
                "recent_audits": recent_count,
                "critical_findings": critical_count,
                "average_score": float(avg_score),
                "recommendations": recommendations,
            }
    
    except Exception as e:
        logger.error(f"Error getting health check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
