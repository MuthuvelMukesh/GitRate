"""90-day remediation roadmap generator."""

from typing import List, Dict, Tuple
from logging import getLogger
from datetime import datetime, timedelta
from enum import Enum

from core.models import AcquisitionAuditResult, AuditFinding, RoadmapTask
from report_generators.base_report_generator import BaseReportGenerator

logger = getLogger(__name__)


class RemediationPriority(str, Enum):
    """Remediation priority levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RoadmapGenerator(BaseReportGenerator):
    """Generate 90-day remediation roadmaps.
    
    Creates:
    - Prioritized task list
    - Weekly breakdown
    - Resource estimates
    - Dependency tracking
    - Success metrics
    """

    def __init__(self,
                 audit_result: AcquisitionAuditResult,
                 team_size: int = 3,
                 hours_per_week: float = 40.0,
                 company_name: str = "GitRate"):
        """Initialize roadmap generator.
        
        Args:
            audit_result: Complete audit result
            team_size: Number of developers available
            hours_per_week: Development hours per week
            company_name: Organization name
        """
        super().__init__(audit_result, company_name)
        self.team_size = team_size
        self.hours_per_week = hours_per_week
        self.total_capacity_per_week = team_size * hours_per_week
        self.start_date = datetime.utcnow()

    async def generate(self) -> List[RoadmapTask]:
        """Generate complete 90-day roadmap.
        
        Returns:
            List of prioritized roadmap tasks
        """
        self.log_info("Generating 90-day remediation roadmap")
        
        try:
            # 1. Categorize findings by priority and domain
            prioritized_findings = await self._prioritize_findings()
            
            # 2. Group into tasks (5-20 hours per task)
            tasks = await self._group_into_tasks(prioritized_findings)
            
            # 3. Schedule across weeks
            scheduled_tasks = await self._schedule_tasks(tasks)
            
            # 4. Track dependencies and risks
            finalized_tasks = await self._add_dependencies(scheduled_tasks)
            
            self.log_info(f"Generated {len(finalized_tasks)} tasks across 13 weeks")
            return finalized_tasks
            
        except Exception as e:
            self.log_error(f"Roadmap generation failed: {str(e)}")
            raise

    async def _prioritize_findings(self) -> Dict[str, List[AuditFinding]]:
        """Group findings by priority level.
        
        Returns:
            Dict mapping priority level -> findings
        """
        prioritized = {
            RemediationPriority.CRITICAL: [],
            RemediationPriority.HIGH: [],
            RemediationPriority.MEDIUM: [],
            RemediationPriority.LOW: [],
        }
        
        for finding in self.audit_result.findings:
            if finding.severity == "CRITICAL":
                prioritized[RemediationPriority.CRITICAL].append(finding)
            elif finding.severity == "HIGH":
                prioritized[RemediationPriority.HIGH].append(finding)
            elif finding.severity == "MEDIUM":
                prioritized[RemediationPriority.MEDIUM].append(finding)
            else:
                prioritized[RemediationPriority.LOW].append(finding)
        
        # Sort within priority by hours (highest first)
        for priority in prioritized:
            prioritized[priority].sort(
                key=lambda f: f.estimation_hours,
                reverse=True
            )
        
        return prioritized

    async def _group_into_tasks(self, prioritized: Dict[str, List[AuditFinding]]) -> List[RoadmapTask]:
        """Group findings into management-friendly tasks.
        
        Args:
            prioritized: Findings grouped by priority
        
        Returns:
            List of roadmap tasks (5-20 hours each)
        """
        tasks = []
        task_id = 1
        
        # Process in priority order
        for priority in [RemediationPriority.CRITICAL, RemediationPriority.HIGH,
                         RemediationPriority.MEDIUM, RemediationPriority.LOW]:
            
            findings = prioritized[priority]
            current_task_findings = []
            current_hours = 0
            
            for finding in findings:
                # Start new task if current would exceed 20 hours
                if current_hours + finding.estimation_hours > 20 and current_task_findings:
                    tasks.append(self._create_task(
                        task_id, current_task_findings, priority
                    ))
                    task_id += 1
                    current_task_findings = []
                    current_hours = 0
                
                current_task_findings.append(finding)
                current_hours += finding.estimation_hours
            
            # Add remaining findings as task
            if current_task_findings:
                tasks.append(self._create_task(
                    task_id, current_task_findings, priority
                ))
                task_id += 1
        
        return tasks

    def _create_task(self, task_id: int, findings: List[AuditFinding], priority: RemediationPriority) -> RoadmapTask:
        """Create a roadmap task from grouped findings.
        
        Args:
            task_id: Unique task identifier
            findings: List of related findings
            priority: Task priority
        
        Returns:
            RoadmapTask object
        """
        total_hours = sum(f.estimation_hours for f in findings)
        categories = set(f.category for f in findings)
        
        # Generate task title
        if len(findings) == 1:
            title = findings[0].title
        else:
            category = list(categories)[0] if categories else "Remediation"
            title = f"{category} - Multiple Issues ({len(findings)} findings)"
        
        # Generate description
        description = "\n".join([
            f"• {f.title}: {f.recommendation}"
            for f in findings[:3]
        ])
        if len(findings) > 3:
            description += f"\n• ... and {len(findings) - 3} more"
        
        return RoadmapTask(
            task_id=task_id,
            title=title,
            description=description,
            priority=priority.value,
            estimated_hours=total_hours,
            week=1,  # Will be scheduled later
            dependencies=[],
            category=list(categories)[0] if categories else "General",
            success_criteria=self._generate_success_criteria(findings),
        )

    def _generate_success_criteria(self, findings: List[AuditFinding]) -> List[str]:
        """Generate success criteria from findings.
        
        Args:
            findings: List of findings for task
        
        Returns:
            List of success criteria
        """
        criteria = []
        
        # Category-specific criteria
        categories = set(f.category for f in findings)
        
        if "Security" in categories:
            criteria.append("No known CVEs in dependencies")
            criteria.append("No secrets exposed in code")
        
        if "Code Quality" in categories:
            criteria.append("Test coverage ≥ 70%")
            criteria.append("All critical code files reviewed")
        
        if "Team Sustainability" in categories:
            criteria.append("Documentation complete")
            criteria.append("Knowledge shared across team")
        
        if "IP & Legal" in categories:
            criteria.append("License compliance verified")
            criteria.append("Attribution review complete")
        
        return criteria[:3]  # Top 3 criteria

    async def _schedule_tasks(self, tasks: List[RoadmapTask]) -> List[RoadmapTask]:
        """Schedule tasks across 13 weeks based on capacity.
        
        Args:
            tasks: Unscheduled tasks
        
        Returns:
            Scheduled tasks
        """
        scheduled = []
        week_capacity = {w: self.total_capacity_per_week for w in range(1, 14)}
        
        # Schedule critical tasks first
        for task in sorted(tasks, key=lambda t: (
            {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(t.priority, 4),
            -t.estimated_hours
        )):
            # Find first week with capacity
            for week in range(1, 14):
                if week_capacity[week] >= task.estimated_hours:
                    task.week = week
                    week_capacity[week] -= task.estimated_hours
                    scheduled.append(task)
                    break
            
            # If no week has capacity, put in earliest week and flag as at-risk
            if not hasattr(task, 'week') or task.week is None:
                task.week = min(week_capacity, key=week_capacity.get)
                task.at_risk = True
                scheduled.append(task)
        
        return scheduled

    async def _add_dependencies(self, tasks: List[RoadmapTask]) -> List[RoadmapTask]:
        """Add task dependencies and risk factors.
        
        Args:
            tasks: Scheduled tasks
        
        Returns:
            Tasks with dependencies noted
        """
        # Add logical dependencies
        category_first_task = {}
        
        for task in sorted(tasks, key=lambda t: t.week):
            # First task in each category sets up infrastructure
            if task.category not in category_first_task:
                category_first_task[task.category] = task.task_id
            else:
                # Subsequent tasks depend on first task
                task.dependencies.append(category_first_task[task.category])
        
        # Add risk flags
        for task in tasks:
            if task.priority == "CRITICAL" and task.week > 4:
                task.at_risk = True
                task.risk_note = "Critical issue scheduled for late remediation"
            
            if task.estimated_hours > self.total_capacity_per_week:
                task.at_risk = True
                task.risk_note = "Task exceeds single week capacity"
        
        return tasks

    def get_roadmap_summary(self, tasks: List[RoadmapTask]) -> Dict:
        """Get summary statistics for roadmap.
        
        Args:
            tasks: Complete roadmap tasks
        
        Returns:
            Summary dict with metrics
        """
        by_priority = {}
        by_week = {}
        
        for task in tasks:
            # By priority
            priority = task.priority
            if priority not in by_priority:
                by_priority[priority] = {"count": 0, "hours": 0}
            by_priority[priority]["count"] += 1
            by_priority[priority]["hours"] += task.estimated_hours
            
            # By week
            week = task.week
            if week not in by_week:
                by_week[week] = {"count": 0, "hours": 0}
            by_week[week]["count"] += 1
            by_week[week]["hours"] += task.estimated_hours
        
        total_hours = sum(t.estimated_hours for t in tasks)
        weeks_needed = next((w for w in range(1, 14) if sum(
            by_week.get(w, {}).get("hours", 0) for w in range(1, w+1)
        ) >= total_hours), 13)
        
        return {
            "total_tasks": len(tasks),
            "total_hours": total_hours,
            "estimated_completion_week": weeks_needed,
            "estimated_completion_date": (self.start_date + timedelta(weeks=weeks_needed)).strftime("%B %d, %Y"),
            "by_priority": by_priority,
            "by_week": by_week,
            "weekly_capacity": self.total_capacity_per_week,
            "team_size": self.team_size,
            "at_risk_tasks": len([t for t in tasks if getattr(t, 'at_risk', False)]),
        }

    def get_executive_summary(self, tasks: List[RoadmapTask]) -> str:
        """Generate executive summary of roadmap.
        
        Args:
            tasks: Complete roadmap tasks
        
        Returns:
            Summary text
        """
        summary = self.get_roadmap_summary(tasks)
        
        critical_tasks = [t for t in tasks if t.priority == "CRITICAL"]
        
        text = f"""
REMEDIATION ROADMAP SUMMARY

Total Remediation Effort: {summary['total_hours']} hours ({summary['total_hours']/40:.1f} weeks)

Estimated Timeline:
- Start Date: {self.start_date.strftime('%B %d, %Y')}
- Completion Date: {summary['estimated_completion_date']}
- Team Size: {self.team_size} developers
- Weekly Capacity: {self.total_capacity_per_week} hours

Task Breakdown:
- Critical Tasks: {summary['by_priority'].get('CRITICAL', {}).get('count', 0)} tasks ({summary['by_priority'].get('CRITICAL', {}).get('hours', 0)} hours)
- High Priority: {summary['by_priority'].get('HIGH', {}).get('count', 0)} tasks ({summary['by_priority'].get('HIGH', {}).get('hours', 0)} hours)
- Medium Priority: {summary['by_priority'].get('MEDIUM', {}).get('count', 0)} tasks ({summary['by_priority'].get('MEDIUM', {}).get('hours', 0)} hours)
- Low Priority: {summary['by_priority'].get('LOW', {}).get('count', 0)} tasks ({summary['by_priority'].get('LOW', {}).get('hours', 0)} hours)

Risk Assessment:
- At-Risk Tasks: {summary['at_risk_tasks']}
- Critical Path Length: {len(critical_tasks)} blocking tasks

CRITICAL PATH (Must Complete First):
"""
        for task in critical_tasks[:3]:
            text += f"\n- Week {task.week}: {task.title}"
        
        return text
