"""Shared utility functions and helpers."""

import re
from typing import Optional, Tuple
from datetime import datetime, timedelta


def parse_github_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse a GitHub URL and extract owner and repo name.
    
    Supports:
    - https://github.com/owner/repo
    - https://github.com/owner/repo.git
    - git@github.com:owner/repo.git
    
    Args:
        url: GitHub repository URL
        
    Returns:
        Tuple of (owner, repo, error_message)
    """
    if not url or not isinstance(url, str):
        return None, None, "Invalid URL format"

    url = url.strip()
    
    # Handle git@github.com: format
    if url.startswith("git@github.com:"):
        try:
            path = url.replace("git@github.com:", "").replace(".git", "")
            parts = path.split("/")
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].strip(), None
        except Exception:
            pass
    
    # Handle HTTPS format
    if "github.com" in url.lower():
        # Clean URL
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        
        # Extract path after github.com
        match = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:/|\.git)?$", url, re.IGNORECASE)
        if match:
            owner, repo = match.groups()
            return owner.strip(), repo.strip(), None
    
    return None, None, "Not a valid GitHub URL"


def estimate_hours_to_fix(
    lines_of_code: int,
    complexity: float,
    test_coverage: float,
    has_documentation: bool = False,
) -> int:
    """
    Estimate hours to refactor/fix code.
    
    Formula:
    - Base: 5 hours per 100 LOC
    - Complexity multiplier: complexity / 5
    - Test coverage penalty: (100 - coverage) / 100 * 10
    - Documentation bonus: -5 hours if exists
    """
    # Base calculation: 5 hours per 100 LOC
    base_hours = (lines_of_code / 100) * 5
    
    # Complexity multiplier
    complexity_multiplier = max(1.0, complexity / 5)
    
    # Test coverage penalty (missing tests = more work)
    test_penalty = ((100 - test_coverage) / 100) * 10
    
    # Total
    total = base_hours * complexity_multiplier + test_penalty
    
    # Documentation bonus
    if has_documentation:
        total -= 5
    
    return max(1, int(round(total)))


def calculate_risk_score(
    metrics: dict,
    weights: dict = None,
) -> float:
    """
    Calculate risk score (0-100) from multiple metrics.
    
    Args:
        metrics: Dict of metric_name -> score (0-100)
        weights: Dict of metric_name -> weight (default equal)
        
    Returns:
        Weighted risk score (0-100)
    """
    if not metrics:
        return 0.0
    
    if weights is None:
        weights = {key: 1.0 for key in metrics.keys()}
    
    total_weight = sum(weights.get(key, 1.0) for key in metrics.keys())
    if total_weight == 0:
        return 0.0
    
    weighted_sum = sum(
        metrics[key] * weights.get(key, 1.0)
        for key in metrics.keys()
        if key in metrics
    )
    
    return min(100, max(0, weighted_sum / total_weight))


def days_since(date: datetime) -> int:
    """Calculate days since a date."""
    if not date:
        return 0
    return (datetime.utcnow() - date).days


def format_risk_level(score: float) -> str:
    """Convert risk score to risk level."""
    if score >= 80:
        return "CRITICAL"
    elif score >= 60:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    else:
        return "LOW"


def sanitize_string(text: str, max_length: int = 500) -> str:
    """Sanitize and truncate string."""
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    return text


def extract_version(version_string: str) -> str:
    """Extract semantic version from various formats."""
    if not version_string:
        return "unknown"
    
    # Try to extract semantic version pattern
    match = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_string)
    if match:
        return match.group(1)
    
    return version_string


def normalize_package_name(name: str) -> str:
    """Normalize package name for consistency."""
    if not name:
        return ""
    return name.lower().replace("_", "-").strip()


def is_valid_commit_hash(commit_hash: str) -> bool:
    """Check if string is a valid git commit hash."""
    return bool(re.match(r"^[0-9a-f]{40}$", commit_hash.lower()))


def calculate_age_percentage(
    item_age_days: int,
    threshold_days: int,
) -> float:
    """
    Calculate how far past a threshold an item is.
    
    Returns percentage over threshold (0-100+)
    """
    if threshold_days <= 0:
        return 0
    percentage = (item_age_days / threshold_days) * 100
    return min(200, percentage)  # Cap at 200%
