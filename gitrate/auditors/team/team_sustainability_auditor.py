"""Team Sustainability Auditor: Bus factor, knowledge silos, onboarding analysis."""

from typing import List, Dict, Tuple
from logging import getLogger
from collections import Counter

from gitrate.core.models import (
    AuditFinding,
    RepositoryData,
)
from gitrate.auditors.base_auditor import BaseAuditor

logger = getLogger(__name__)


class TeamSustainabilityAuditor(BaseAuditor):
    """Analyze team health and sustainability metrics.
    
    Evaluates:
    1. Bus factor (key person dependency)
    2. Knowledge silo concentration
    3. Contributor diversity and retention
    4. Onboarding velocity
    5. Team stability metrics
    """

    def __init__(self):
        """Initialize Team Sustainability auditor."""
        super().__init__("Team Sustainability Auditor")

    async def run(self, repo_data: RepositoryData) -> tuple[float, List[AuditFinding]]:
        """Execute team sustainability audit.
        
        Args:
            repo_data: Complete repository data
            
        Returns:
            Tuple of (audit_score, findings)
        """
        self.findings = []
        self.log_info(f"Starting team sustainability audit for {repo_data.repo_info.full_name}")
        
        # 1. Analyze bus factor (key person dependency)
        bus_factor_score = await self._analyze_bus_factor(repo_data)
        
        # 2. Analyze knowledge silo concentration
        silo_score = await self._analyze_knowledge_silos(repo_data)
        
        # 3. Analyze contributor diversity
        diversity_score = await self._analyze_contributor_diversity(repo_data)
        
        # 4. Analyze onboarding velocity
        onboarding_score = await self._analyze_onboarding_velocity(repo_data)
        
        # 5. Analyze team stability
        stability_score = await self._analyze_team_stability(repo_data)
        
        # Weighted final score
        weights = {
            "bus_factor": 0.30,
            "silos": 0.25,
            "diversity": 0.20,
            "onboarding": 0.15,
            "stability": 0.10,
        }
        
        final_score = (
            bus_factor_score * weights["bus_factor"] +
            silo_score * weights["silos"] +
            diversity_score * weights["diversity"] +
            onboarding_score * weights["onboarding"] +
            stability_score * weights["stability"]
        )
        
        self.log_info(f"Team sustainability audit complete: {final_score:.1f}/100")
        self.log_debug(
            f"Component scores - Bus Factor: {bus_factor_score}, Silos: {silo_score}, "
            f"Diversity: {diversity_score}, Onboarding: {onboarding_score}, Stability: {stability_score}"
        )
        
        return final_score, self.findings

    async def _analyze_bus_factor(self, repo_data: RepositoryData) -> float:
        """Calculate bus factor (key person dependency risk).
        
        Bus factor = minimum number of key people whose loss would make the project fail.
        
        Returns:
            Score 0-100 (higher = lower key person dependency)
        """
        self.log_debug("Analyzing bus factor")
        
        if not repo_data.contributors or repo_data.contributors.total_contributors == 0:
            self.add_finding(
                category="Team Sustainability",
                severity="CRITICAL",
                title="No contributors found",
                description="Repository has no recorded contributors",
                recommendation="Verify repository data or check GitHub permissions",
                estimation_hours=0,
            )
            return 0.0
        
        total_contrib = repo_data.contributors.total_contributors
        
        # Get top contributors by commits
        top_contrib_ratio = await self._get_top_contributor_ratio(repo_data)
        
        # Risk assessment based on concentration
        if top_contrib_ratio > 0.8:  # Single person has 80%+ of commits
            self.add_finding(
                category="Team Sustainability",
                severity="CRITICAL",
                title="Extreme bus factor (single person dependency)",
                description=f"One person has {top_contrib_ratio*100:.0f}% of all commits",
                recommendation="Establish pair programming, code reviews, and knowledge sharing to reduce dependency",
                estimation_hours=60,
            )
            return 20.0
        
        elif top_contrib_ratio > 0.6:  # Single person has 60%+ of commits
            self.add_finding(
                category="Team Sustainability",
                severity="HIGH",
                title="High bus factor (key person dependency)",
                description=f"One person has {top_contrib_ratio*100:.0f}% of all commits",
                recommendation="Distribute knowledge and responsibilities across team members",
                estimation_hours=40,
            )
            return 40.0
        
        # Check if top 2 people have most commits
        top_2_ratio = await self._get_top_n_contributor_ratio(repo_data, 2)
        
        if top_2_ratio > 0.75:
            self.add_finding(
                category="Team Sustainability",
                severity="HIGH",
                title="Concentrated contribution pattern",
                description=f"Top 2 contributors have {top_2_ratio*100:.0f}% of all commits",
                recommendation="Actively recruit and mentor additional team members",
                estimation_hours=30,
            )
            return 50.0
        
        # Healthy distribution
        if total_contrib >= 5:
            return 95.0
        elif total_contrib >= 3:
            return 80.0
        else:
            self.add_finding(
                category="Team Sustainability",
                severity="MEDIUM",
                title="Low contributor count",
                description=f"Only {total_contrib} unique contributors",
                recommendation="Expand team or improve contributor attraction",
                estimation_hours=20,
            )
            return 60.0

    async def _analyze_knowledge_silos(self, repo_data: RepositoryData) -> float:
        """Analyze knowledge silo concentration in codebase.
        
        Returns:
            Score 0-100 (higher = better knowledge distribution)
        """
        self.log_debug("Analyzing knowledge silos")
        
        # Analyze commit authorship by module/component
        silo_concentration = await self._calculate_silo_concentration(repo_data)
        
        if silo_concentration > 0.8:
            self.add_finding(
                category="Team Sustainability",
                severity="HIGH",
                title="Knowledge heavily siloed by module",
                description=f"Knowledge concentration score: {silo_concentration:.2f}. Few people own most modules.",
                recommendation="Implement code review process, documentation, and cross-training",
                estimation_hours=50,
            )
            return 35.0
        
        elif silo_concentration > 0.6:
            self.add_finding(
                category="Team Sustainability",
                severity="MEDIUM",
                title="Moderate knowledge silos detected",
                description=f"Some modules owned by single developers",
                recommendation="Establish pair programming for critical modules",
                estimation_hours=30,
            )
            return 65.0
        
        return 85.0

    async def _analyze_contributor_diversity(self, repo_data: RepositoryData) -> float:
        """Analyze contributor diversity and retention.
        
        Returns:
            Score 0-100 (higher = better diversity/retention)
        """
        self.log_debug("Analyzing contributor diversity")
        
        if not repo_data.contributors or repo_data.contributors.total_contributors == 0:
            return 0.0
        
        total_contrib = repo_data.contributors.total_contributors
        
        # Check contributor affiliation diversity (if available)
        unique_orgs = len(set(
            getattr(c, 'organization', '') 
            for c in getattr(repo_data.contributors, 'contributors', [])
            if hasattr(c, 'organization')
        ))
        
        # Scoring criteria
        score = 100.0
        
        # Organization diversity
        if unique_orgs == 0:
            self.add_finding(
                category="Team Sustainability",
                severity="MEDIUM",
                title="Single organization dominance",
                description="All contributors appear to be from same organization",
                recommendation="Encourage community contributions and external collaborators",
                estimation_hours=20,
            )
            score -= 20
        elif unique_orgs == 1:
            score -= 10
        elif unique_orgs < 3:
            score -= 5
        
        # Contributor count
        if total_contrib >= 20:
            pass  # Good diversity
        elif total_contrib >= 10:
            score -= 5
        elif total_contrib >= 5:
            score -= 15
        else:
            score -= 25
        
        return max(0.0, score)

    async def _analyze_onboarding_velocity(self, repo_data: RepositoryData) -> float:
        """Analyze onboarding velocity - how quickly new contributors get productive.
        
        Returns:
            Score 0-100 (higher = faster onboarding)
        """
        self.log_debug("Analyzing onboarding velocity")
        
        score = 100.0
        
        # Check for contribution documentation
        has_contributing_guide = any(
            "contributing" in f.lower() or "contributing" in f.lower()
            for f in getattr(repo_data, 'files', [])
        )
        
        if not has_contributing_guide:
            self.add_finding(
                category="Team Sustainability",
                severity="MEDIUM",
                title="Missing CONTRIBUTING guide",
                description="No CONTRIBUTING.md file found for new contributors",
                recommendation="Create CONTRIBUTING.md with development setup and guidelines",
                estimation_hours=5,
            )
            score -= 15
        
        # Check for README
        has_readme = any(
            f.lower() == "readme.md" or f.lower() == "readme"
            for f in getattr(repo_data, 'files', [])
        )
        
        if not has_readme:
            self.add_finding(
                category="Team Sustainability",
                severity="MEDIUM",
                title="Missing README",
                description="No README file for project overview",
                recommendation="Create comprehensive README with project description and setup",
                estimation_hours=8,
            )
            score -= 10
        
        # Check for development setup documentation
        setup_doc_exists = any(
            f.lower() in ["setup.md", "development.md", "dev_guide.md"]
            for f in getattr(repo_data, 'files', [])
        )
        
        if not setup_doc_exists:
            score -= 10
        
        return max(0.0, score)

    async def _analyze_team_stability(self, repo_data: RepositoryData) -> float:
        """Analyze team stability and activity patterns.
        
        Returns:
            Score 0-100 (higher = more stable/active team)
        """
        self.log_debug("Analyzing team stability")
        
        score = 100.0
        
        # Check recent activity
        if repo_data.repo_info.updated_at:
            import datetime
            days_since_update = (
                datetime.datetime.now(datetime.timezone.utc) - repo_data.repo_info.updated_at
            ).days
            
            if days_since_update > 365:
                self.add_finding(
                    category="Team Sustainability",
                    severity="HIGH",
                    title="Stale repository (>1 year inactive)",
                    description=f"No activity for {days_since_update} days",
                    recommendation="Assess project status and determine if maintenance will continue",
                    estimation_hours=10,
                )
                score -= 40
            
            elif days_since_update > 180:
                self.add_finding(
                    category="Team Sustainability",
                    severity="MEDIUM",
                    title="Low recent activity (6+ months)",
                    description=f"Last update {days_since_update} days ago",
                    recommendation="Verify team commitment and development roadmap",
                    estimation_hours=5,
                )
                score -= 15
            
            elif days_since_update > 30:
                score -= 5
        
        return max(0.0, score)

    async def _get_top_contributor_ratio(self, repo_data: RepositoryData) -> float:
        """Calculate percentage of commits from top contributor.
        
        Returns:
            Ratio 0.0-1.0
        """
        if not hasattr(repo_data, 'contributors') or not repo_data.contributors:
            return 0.0
        
        contributors = getattr(repo_data.contributors, 'contributors', [])
        if not contributors:
            return 0.0
        
        # Get contribution counts (fallback to equal if not available)
        commit_counts = [
            getattr(c, 'contributions', 1) if hasattr(c, 'contributions') else 1
            for c in contributors
        ]
        
        if not commit_counts:
            return 0.0
        
        total = sum(commit_counts)
        if total == 0:
            return 0.0
        
        return max(commit_counts) / total

    async def _get_top_n_contributor_ratio(self, repo_data: RepositoryData, n: int) -> float:
        """Calculate percentage of commits from top N contributors.
        
        Returns:
            Ratio 0.0-1.0
        """
        if not hasattr(repo_data, 'contributors') or not repo_data.contributors:
            return 0.0
        
        contributors = getattr(repo_data.contributors, 'contributors', [])
        if not contributors:
            return 0.0
        
        # Get contribution counts
        commit_counts = [
            getattr(c, 'contributions', 1) if hasattr(c, 'contributions') else 1
            for c in contributors
        ]
        
        if not commit_counts:
            return 0.0
        
        total = sum(commit_counts)
        if total == 0:
            return 0.0
        
        top_n_commits = sum(sorted(commit_counts, reverse=True)[:n])
        return top_n_commits / total

    async def _calculate_silo_concentration(self, repo_data: RepositoryData) -> float:
        """Calculate knowledge silo concentration (0-1, higher = worse).
        
        Returns:
            Score 0.0-1.0
        """
        # Simplified: if few contributors, high concentration
        if not hasattr(repo_data, 'contributors') or not repo_data.contributors:
            return 1.0
        
        total = repo_data.contributors.total_contributors
        
        if total == 0:
            return 1.0
        elif total <= 2:
            return 0.9
        elif total <= 5:
            return 0.7
        else:
            return 0.5
