"""Dashboard routes and API endpoints for audit visualization."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from gitrate.core.audit_engine import AuditEngine
from gitrate.database.session import AsyncSessionLocal
from gitrate.core.models import AcquisitionAuditResult

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


# ===== RESPONSE MODELS =====

class AuditSummaryResponse(BaseModel):
    """Summary of audit for dashboard display."""
    audit_id: str
    repository: str
    overall_score: float
    ip_legal_score: float
    security_score: float
    code_quality_score: float
    team_sustainability_score: float
    findings_count: int
    critical_findings: int
    created_at: datetime
    duration_seconds: float


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics and summary."""
    total_audits: int
    average_score: float
    critical_findings_count: int
    repositories_audited: int
    audits_this_week: int
    success_rate: float
    average_duration_seconds: float


class AuditComparisonResponse(BaseModel):
    """Comparison between two audits."""
    audit_1: AuditSummaryResponse
    audit_2: AuditSummaryResponse
    score_difference: float
    findings_difference: int
    improvements: List[str]
    regressions: List[str]


# ===== ENDPOINTS =====

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats() -> DashboardStatsResponse:
    """
    Get dashboard statistics and summary.
    
    Returns:
        Dashboard stats with audit summary
    """
    try:
        async with AsyncSessionLocal() as session:
            # Query recent audits
            from sqlalchemy import func, and_
            from gitrate.core.models import Audit
            
            # Get total audits
            total_audits = await session.execute(
                "SELECT COUNT(*) FROM audits"
            )
            total = total_audits.scalar() or 0
            
            # Get average score
            avg_score = await session.execute(
                "SELECT AVG(overall_score) FROM audits"
            )
            average_score = avg_score.scalar() or 0
            
            # Get audits this week
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_audits = await session.execute(
                f"SELECT COUNT(*) FROM audits WHERE created_at > '{week_ago}'"
            )
            audits_this_week = week_audits.scalar() or 0
            
            # Get unique repositories
            unique_repos = await session.execute(
                "SELECT COUNT(DISTINCT repository) FROM audits"
            )
            repositories_audited = unique_repos.scalar() or 0
            
            # Success rate (audits without critical errors)
            success = await session.execute(
                "SELECT COUNT(*) FROM audits WHERE status = 'COMPLETED'"
            )
            successful = success.scalar() or 0
            success_rate = (successful / total * 100) if total > 0 else 0
            
            # Average duration
            avg_duration = await session.execute(
                "SELECT AVG(duration_seconds) FROM audits"
            )
            average_duration = avg_duration.scalar() or 0
            
            # Critical findings
            critical_findings = await session.execute(
                "SELECT COUNT(*) FROM findings WHERE severity = 'CRITICAL'"
            )
            critical_count = critical_findings.scalar() or 0
            
            logger.info("Dashboard stats retrieved")
            
            return DashboardStatsResponse(
                total_audits=total,
                average_score=float(average_score),
                critical_findings_count=critical_count,
                repositories_audited=repositories_audited,
                audits_this_week=audits_this_week,
                success_rate=success_rate,
                average_duration_seconds=float(average_duration or 0),
            )
    
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audits", response_model=List[AuditSummaryResponse])
async def get_recent_audits(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repository: Optional[str] = None,
    min_score: Optional[float] = None,
) -> List[AuditSummaryResponse]:
    """
    Get recent audits with optional filtering.
    
    Args:
        limit: Maximum audits to return
        offset: Number of audits to skip
        repository: Filter by repository name
        min_score: Filter by minimum score
    
    Returns:
        List of audit summaries
    """
    try:
        async with AsyncSessionLocal() as session:
            # Build query
            query = "SELECT * FROM audits WHERE 1=1"
            params = []
            
            if repository:
                query += " AND repository ILIKE %s"
                params.append(f"%{repository}%")
            
            if min_score is not None:
                query += " AND overall_score >= %s"
                params.append(min_score)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            result = await session.execute(query, params)
            audits = result.fetchall()
            
            summaries = [
                AuditSummaryResponse(
                    audit_id=audit[0],
                    repository=audit[1],
                    overall_score=float(audit[2]),
                    ip_legal_score=float(audit[3]),
                    security_score=float(audit[4]),
                    code_quality_score=float(audit[5]),
                    team_sustainability_score=float(audit[6]),
                    findings_count=audit[7],
                    critical_findings=audit[8],
                    created_at=audit[9],
                    duration_seconds=float(audit[10]),
                )
                for audit in audits
            ]
            
            logger.info(f"Retrieved {len(summaries)} recent audits")
            return summaries
    
    except Exception as e:
        logger.error(f"Error getting recent audits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/{audit_id}", response_model=AuditSummaryResponse)
async def get_audit_summary(audit_id: str) -> AuditSummaryResponse:
    """
    Get detailed audit summary for dashboard.
    
    Args:
        audit_id: Audit identifier
    
    Returns:
        Audit summary with all scores
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                "SELECT * FROM audits WHERE audit_id = %s",
                (audit_id,)
            )
            audit = result.fetchone()
            
            if not audit:
                raise HTTPException(status_code=404, detail="Audit not found")
            
            return AuditSummaryResponse(
                audit_id=audit[0],
                repository=audit[1],
                overall_score=float(audit[2]),
                ip_legal_score=float(audit[3]),
                security_score=float(audit[4]),
                code_quality_score=float(audit[5]),
                team_sustainability_score=float(audit[6]),
                findings_count=audit[7],
                critical_findings=audit[8],
                created_at=audit[9],
                duration_seconds=float(audit[10]),
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison/{audit_id_1}/{audit_id_2}", response_model=AuditComparisonResponse)
async def compare_audits(
    audit_id_1: str,
    audit_id_2: str,
) -> AuditComparisonResponse:
    """
    Compare two audits side-by-side.
    
    Args:
        audit_id_1: First audit ID
        audit_id_2: Second audit ID
    
    Returns:
        Comparison with differences and insights
    """
    try:
        async with AsyncSessionLocal() as session:
            # Get both audits
            result1 = await session.execute(
                "SELECT * FROM audits WHERE audit_id = %s",
                (audit_id_1,)
            )
            audit1 = result1.fetchone()
            
            result2 = await session.execute(
                "SELECT * FROM audits WHERE audit_id = %s",
                (audit_id_2,)
            )
            audit2 = result2.fetchone()
            
            if not audit1 or not audit2:
                raise HTTPException(status_code=404, detail="One or both audits not found")
            
            # Build summaries
            summary1 = AuditSummaryResponse(
                audit_id=audit1[0],
                repository=audit1[1],
                overall_score=float(audit1[2]),
                ip_legal_score=float(audit1[3]),
                security_score=float(audit1[4]),
                code_quality_score=float(audit1[5]),
                team_sustainability_score=float(audit1[6]),
                findings_count=audit1[7],
                critical_findings=audit1[8],
                created_at=audit1[9],
                duration_seconds=float(audit1[10]),
            )
            
            summary2 = AuditSummaryResponse(
                audit_id=audit2[0],
                repository=audit2[1],
                overall_score=float(audit2[2]),
                ip_legal_score=float(audit2[3]),
                security_score=float(audit2[4]),
                code_quality_score=float(audit2[5]),
                team_sustainability_score=float(audit2[6]),
                findings_count=audit2[7],
                critical_findings=audit2[8],
                created_at=audit2[9],
                duration_seconds=float(audit2[10]),
            )
            
            # Calculate differences
            score_diff = summary1.overall_score - summary2.overall_score
            findings_diff = summary1.findings_count - summary2.findings_count
            
            improvements = []
            regressions = []
            
            # Check for improvements
            if summary1.security_score > summary2.security_score:
                improvements.append(f"Security improved by {summary1.security_score - summary2.security_score:.1f}")
            elif summary1.security_score < summary2.security_score:
                regressions.append(f"Security declined by {summary2.security_score - summary1.security_score:.1f}")
            
            if summary1.code_quality_score > summary2.code_quality_score:
                improvements.append(f"Code quality improved by {summary1.code_quality_score - summary2.code_quality_score:.1f}")
            elif summary1.code_quality_score < summary2.code_quality_score:
                regressions.append(f"Code quality declined by {summary2.code_quality_score - summary1.code_quality_score:.1f}")
            
            if findings_diff < 0:
                improvements.append(f"{-findings_diff} findings resolved")
            elif findings_diff > 0:
                regressions.append(f"{findings_diff} new findings")
            
            logger.info(f"Compared audits {audit_id_1} and {audit_id_2}")
            
            return AuditComparisonResponse(
                audit_1=summary1,
                audit_2=summary2,
                score_difference=score_diff,
                findings_difference=findings_diff,
                improvements=improvements,
                regressions=regressions,
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing audits: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-repositories")
async def get_top_repositories(limit: int = Query(10, ge=1, le=50)) -> List[Dict[str, Any]]:
    """
    Get top repositories by score.
    
    Args:
        limit: Maximum repositories to return
    
    Returns:
        Top repositories with latest audit scores
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                f"""
                SELECT repository, MAX(overall_score) as best_score, 
                       MAX(created_at) as latest_audit
                FROM audits
                GROUP BY repository
                ORDER BY best_score DESC
                LIMIT {limit}
                """
            )
            
            repos = result.fetchall()
            
            return [
                {
                    "repository": repo[0],
                    "best_score": float(repo[1]),
                    "latest_audit": repo[2],
                }
                for repo in repos
            ]
    
    except Exception as e:
        logger.error(f"Error getting top repositories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/score-distribution")
async def get_score_distribution() -> Dict[str, int]:
    """
    Get distribution of audit scores (bucketed).
    
    Returns:
        Score distribution with counts
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                """
                SELECT 
                    CASE 
                        WHEN overall_score < 20 THEN '0-20'
                        WHEN overall_score < 40 THEN '20-40'
                        WHEN overall_score < 60 THEN '40-60'
                        WHEN overall_score < 80 THEN '60-80'
                        ELSE '80-100'
                    END as bucket,
                    COUNT(*) as count
                FROM audits
                GROUP BY bucket
                ORDER BY bucket
                """
            )
            
            buckets = result.fetchall()
            
            distribution = {
                "0-20": 0,
                "20-40": 0,
                "40-60": 0,
                "60-80": 0,
                "80-100": 0,
            }
            
            for bucket, count in buckets:
                if bucket:
                    distribution[bucket] = count
            
            return distribution
    
    except Exception as e:
        logger.error(f"Error getting score distribution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/findings-by-category")
async def get_findings_by_category() -> Dict[str, int]:
    """
    Get findings breakdown by category.
    
    Returns:
        Findings count by category
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                """
                SELECT category, COUNT(*) as count
                FROM findings
                GROUP BY category
                ORDER BY count DESC
                """
            )
            
            findings = result.fetchall()
            
            return {
                category: count
                for category, count in findings
            }
    
    except Exception as e:
        logger.error(f"Error getting findings by category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
