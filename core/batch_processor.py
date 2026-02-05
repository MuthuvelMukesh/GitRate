"""Batch audit processor for handling multiple repositories with parallel execution."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.audit_engine import AuditEngine
from core.models import AcquisitionAuditResult

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """Batch processing status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class AuditJob:
    """Single audit job in batch."""
    job_id: str
    owner: str
    repo: str
    status: str = BatchStatus.PENDING.value
    result: Optional[AcquisitionAuditResult] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0


class BatchAuditProcessor:
    """Process multiple audit jobs in parallel with progress tracking."""
    
    def __init__(self, audit_engine: AuditEngine,
                 max_concurrent: int = 3,
                 timeout_seconds: int = 600):
        """Initialize batch processor.
        
        Args:
            audit_engine: AuditEngine instance
            max_concurrent: Maximum concurrent audits
            timeout_seconds: Timeout per audit
        """
        self.engine = audit_engine
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds
        self.jobs: Dict[str, AuditJob] = {}
        self.batch_status = BatchStatus.PENDING
        logger.debug(f"Initialized batch processor (max_concurrent={max_concurrent})")
    
    async def process_batch(self, repositories: List[Dict[str, str]],
                           progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Process multiple repositories in parallel.
        
        Args:
            repositories: List of dicts with 'owner' and 'repo'
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dict with results summary
        """
        logger.info(f"Starting batch audit for {len(repositories)} repositories")
        self.batch_status = BatchStatus.IN_PROGRESS
        
        # Create audit jobs
        for i, repo in enumerate(repositories):
            job_id = f"job_{i:03d}"
            self.jobs[job_id] = AuditJob(
                job_id=job_id,
                owner=repo["owner"],
                repo=repo["repo"],
            )
        
        # Process in parallel with semaphore
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def audit_with_semaphore(job_id: str) -> None:
            async with semaphore:
                await self._process_job(job_id, progress_callback)
        
        # Run all jobs
        tasks = [audit_with_semaphore(job_id) for job_id in self.jobs.keys()]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Finalize
        summary = self._generate_summary()
        self.batch_status = summary["overall_status"]
        
        logger.info(f"Batch complete: {summary['completed']}/{summary['total']} successful")
        return summary
    
    async def _process_job(self, job_id: str, 
                          progress_callback: Optional[Callable] = None) -> None:
        """Process single audit job.
        
        Args:
            job_id: Job identifier
            progress_callback: Optional progress callback
        """
        job = self.jobs[job_id]
        
        try:
            job.status = BatchStatus.IN_PROGRESS.value
            job.started_at = datetime.utcnow()
            
            logger.info(f"[{job_id}] Starting audit: {job.owner}/{job.repo}")
            
            # Run audit with timeout
            try:
                result, error = await asyncio.wait_for(
                    self.engine.run_full_audit(job.owner, job.repo),
                    timeout=self.timeout_seconds
                )
                
                if error:
                    job.status = BatchStatus.FAILED.value
                    job.error = error
                    logger.error(f"[{job_id}] Audit failed: {error}")
                else:
                    job.status = BatchStatus.COMPLETED.value
                    job.result = result
                    logger.info(f"[{job_id}] Audit completed: {result.scores.overall:.1f}/100")
                
            except asyncio.TimeoutError:
                job.status = BatchStatus.FAILED.value
                job.error = f"Audit timeout after {self.timeout_seconds} seconds"
                logger.error(f"[{job_id}] Timeout: {job.error}")
            
        except Exception as e:
            job.status = BatchStatus.FAILED.value
            job.error = str(e)
            logger.error(f"[{job_id}] Exception: {e}", exc_info=True)
        
        finally:
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
            
            # Call progress callback
            if progress_callback:
                try:
                    await progress_callback(job) if asyncio.iscoroutinefunction(progress_callback) else progress_callback(job)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate batch summary.
        
        Returns:
            Summary dict with statistics
        """
        completed = sum(1 for j in self.jobs.values() if j.status == BatchStatus.COMPLETED.value)
        failed = sum(1 for j in self.jobs.values() if j.status == BatchStatus.FAILED.value)
        total = len(self.jobs)
        
        total_duration = sum(j.duration_seconds for j in self.jobs.values())
        avg_duration = total_duration / total if total > 0 else 0
        
        # Calculate average scores for completed audits
        avg_scores = self._calculate_average_scores()
        
        # Determine overall status
        if failed == 0:
            overall_status = BatchStatus.COMPLETED.value
        elif completed > 0:
            overall_status = BatchStatus.PARTIALLY_COMPLETED.value
        else:
            overall_status = BatchStatus.FAILED.value
        
        return {
            "overall_status": overall_status,
            "total": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
            "average_scores": avg_scores,
            "started_at": min(
                (j.started_at for j in self.jobs.values() if j.started_at),
                default=None
            ),
            "completed_at": max(
                (j.completed_at for j in self.jobs.values() if j.completed_at),
                default=None
            ),
            "jobs": {
                job_id: self._job_to_dict(job)
                for job_id, job in self.jobs.items()
            }
        }
    
    def _calculate_average_scores(self) -> Dict[str, float]:
        """Calculate average scores across completed audits.
        
        Returns:
            Dict with average scores
        """
        completed_results = [
            j.result for j in self.jobs.values()
            if j.result and j.status == BatchStatus.COMPLETED.value
        ]
        
        if not completed_results:
            return {}
        
        return {
            "overall": sum(r.scores.overall for r in completed_results) / len(completed_results),
            "ip_legal": sum(r.scores.ip_legal for r in completed_results) / len(completed_results),
            "security": sum(r.scores.security for r in completed_results) / len(completed_results),
            "code_quality": sum(r.scores.code_quality for r in completed_results) / len(completed_results),
            "team_sustainability": sum(r.scores.team_sustainability for r in completed_results) / len(completed_results),
        }
    
    def _job_to_dict(self, job: AuditJob) -> Dict[str, Any]:
        """Convert job to dictionary.
        
        Args:
            job: Audit job
        
        Returns:
            Dict representation
        """
        return {
            "job_id": job.job_id,
            "repository": f"{job.owner}/{job.repo}",
            "status": job.status,
            "error": job.error,
            "duration_seconds": job.duration_seconds,
            "score": job.result.scores.overall if job.result else None,
            "findings_count": len(job.result.findings) if job.result else None,
        }
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current batch progress.
        
        Returns:
            Progress dict
        """
        completed = sum(1 for j in self.jobs.values() if j.status == BatchStatus.COMPLETED.value)
        failed = sum(1 for j in self.jobs.values() if j.status == BatchStatus.FAILED.value)
        total = len(self.jobs)
        
        return {
            "status": self.batch_status.value,
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": total - completed - failed,
            "progress_percent": (completed + failed) / total * 100 if total > 0 else 0,
            "jobs": {
                job_id: {
                    "status": job.status,
                    "repository": f"{job.owner}/{job.repo}",
                }
                for job_id, job in self.jobs.items()
            }
        }
    
    def get_job_result(self, job_id: str) -> Optional[AcquisitionAuditResult]:
        """Get result for specific job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            Audit result or None
        """
        if job_id in self.jobs:
            return self.jobs[job_id].result
        return None
    
    async def cancel_batch(self) -> None:
        """Cancel batch processing.
        
        Note: Already running jobs will complete
        """
        self.batch_status = BatchStatus.CANCELLED
        logger.info("Batch processing cancelled")
    
    def get_failed_repositories(self) -> List[Dict[str, Any]]:
        """Get list of failed audit repositories.
        
        Returns:
            List of failed jobs with error info
        """
        failed = [
            {
                "owner": job.owner,
                "repo": job.repo,
                "error": job.error,
            }
            for job in self.jobs.values()
            if job.status == BatchStatus.FAILED.value
        ]
        return failed
    
    def retry_failed(self, progress_callback: Optional[Callable] = None) -> None:
        """Retry failed audits.
        
        Args:
            progress_callback: Optional progress callback
        """
        failed_repos = [
            {"owner": job.owner, "repo": job.repo}
            for job in self.jobs.values()
            if job.status == BatchStatus.FAILED.value
        ]
        
        if failed_repos:
            logger.info(f"Retrying {len(failed_repos)} failed audits")
            # This would need to be awaited in async context
            return self.process_batch(failed_repos, progress_callback)
