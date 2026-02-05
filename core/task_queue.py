"""Async task queue for background audit jobs and report generation."""

import asyncio
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enum."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRY = "RETRY"


class TaskPriority(str, Enum):
    """Task priority enum."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Task:
    """Background task representation."""
    task_id: str
    task_type: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dict representation
        """
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "data": self.data,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


class TaskQueue:
    """In-memory task queue for background jobs."""
    
    def __init__(self, max_workers: int = 3):
        """Initialize task queue.
        
        Args:
            max_workers: Maximum concurrent task workers
        """
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.pending_queue: List[str] = []  # Task IDs ordered by priority
        self.running_count = 0
        self.handlers: Dict[str, Callable] = {}
        logger.info(f"Initialized TaskQueue with {max_workers} workers")
    
    def register_handler(self, task_type: str, 
                        handler: Callable) -> None:
        """Register handler for task type.
        
        Args:
            task_type: Task type identifier
            handler: Async handler function
        """
        self.handlers[task_type] = handler
        logger.debug(f"Registered handler for task type: {task_type}")
    
    async def enqueue(self, task_type: str,
                     data: Optional[Dict[str, Any]] = None,
                     priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """Add task to queue.
        
        Args:
            task_type: Type of task
            data: Task data
            priority: Task priority
        
        Returns:
            Task ID
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=datetime.utcnow(),
            data=data or {},
        )
        
        self.tasks[task_id] = task
        self._insert_in_queue(task_id)
        
        logger.info(f"Enqueued task: {task_id} (type={task_type}, priority={priority.value})")
        
        return task_id
    
    def _insert_in_queue(self, task_id: str) -> None:
        """Insert task in queue maintaining priority order.
        
        Args:
            task_id: Task ID to insert
        """
        task = self.tasks[task_id]
        
        # Find correct position based on priority
        priority_order = {TaskPriority.CRITICAL: 0, TaskPriority.HIGH: 1,
                         TaskPriority.NORMAL: 2, TaskPriority.LOW: 3}
        
        insert_pos = len(self.pending_queue)
        for i, queued_id in enumerate(self.pending_queue):
            if priority_order[task.priority] < priority_order[self.tasks[queued_id].priority]:
                insert_pos = i
                break
        
        self.pending_queue.insert(insert_pos, task_id)
    
    async def start_workers(self) -> None:
        """Start worker tasks to process queue.
        
        This should be called once at application startup.
        """
        workers = [self._worker() for _ in range(self.max_workers)]
        await asyncio.gather(*workers)
    
    async def _worker(self) -> None:
        """Worker task that processes queue.
        
        Continuously processes tasks from queue until shutdown.
        """
        while True:
            try:
                # Wait for task to be available
                while not self.pending_queue or self.running_count >= self.max_workers:
                    await asyncio.sleep(0.1)
                
                # Get next task
                task_id = self.pending_queue.pop(0)
                await self._execute_task(task_id)
                
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _execute_task(self, task_id: str) -> None:
        """Execute a single task.
        
        Args:
            task_id: Task ID to execute
        """
        task = self.tasks[task_id]
        
        try:
            if task.task_type not in self.handlers:
                raise ValueError(f"No handler for task type: {task.task_type}")
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            self.running_count += 1
            
            logger.info(f"Executing task: {task_id}")
            
            # Execute handler
            handler = self.handlers[task.task_type]
            result = await handler(task.data)
            
            # Mark completed
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            logger.info(f"Task completed: {task_id}")
            
        except Exception as e:
            logger.error(f"Task failed: {task_id}: {str(e)}", exc_info=True)
            
            # Retry if not exceeded max retries
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRY
                task.error = str(e)
                self._insert_in_queue(task_id)
                logger.info(f"Retrying task: {task_id} (attempt {task.retry_count})")
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.utcnow()
                logger.error(f"Task failed permanently: {task_id}")
        
        finally:
            self.running_count -= 1
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID.
        
        Args:
            task_id: Task ID
        
        Returns:
            Task or None
        """
        return self.tasks.get(task_id)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status.
        
        Returns:
            Queue status dict
        """
        by_status = {}
        for task in self.tasks.values():
            status_val = task.status.value
            if status_val not in by_status:
                by_status[status_val] = 0
            by_status[status_val] += 1
        
        return {
            "total_tasks": len(self.tasks),
            "pending": len(self.pending_queue),
            "running": self.running_count,
            "by_status": by_status,
            "workers": {
                "max": self.max_workers,
                "active": self.running_count
            }
        }
    
    def get_tasks(self, status: Optional[TaskStatus] = None,
                 task_type: Optional[str] = None,
                 limit: int = 100) -> List[Task]:
        """Get tasks with optional filtering.
        
        Args:
            status: Filter by status
            task_type: Filter by task type
            limit: Maximum tasks to return
        
        Returns:
            List of tasks
        """
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        
        # Sort by created date descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        
        return tasks[:limit]
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.
        
        Args:
            task_id: Task ID
        
        Returns:
            True if cancelled, False if not possible
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RETRY]:
            task.status = TaskStatus.CANCELLED
            if task_id in self.pending_queue:
                self.pending_queue.remove(task_id)
            logger.info(f"Cancelled task: {task_id}")
            return True
        
        return False
    
    def cleanup_old_tasks(self, days: int = 7) -> int:
        """Remove old completed tasks.
        
        Args:
            days: Remove tasks older than N days
        
        Returns:
            Number of tasks removed
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
            and task.completed_at and task.completed_at < cutoff
        ]
        
        for task_id in to_remove:
            del self.tasks[task_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks")
        
        return len(to_remove)


# Global task queue instance
task_queue = TaskQueue(max_workers=3)
