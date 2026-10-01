"""Unit tests for helper functions."""

import pytest
from datetime import datetime, timedelta

from gitrate.utils.helpers import (
    parse_github_url,
    estimate_hours_to_fix,
    calculate_risk_score,
    days_since,
    format_risk_level,
    sanitize_string,
    extract_version,
    normalize_package_name,
    is_valid_commit_hash,
    calculate_age_percentage,
)


class TestParseGithubUrl:
    """Tests for parse_github_url function."""
    
    def test_parse_https_url(self):
        """Test parsing HTTPS GitHub URL."""
        owner, repo, error = parse_github_url("https://github.com/pytorch/pytorch")
        assert owner == "pytorch"
        assert repo == "pytorch"
        assert error is None
    
    def test_parse_http_url(self):
        """Test parsing HTTP GitHub URL."""
        owner, repo, error = parse_github_url("http://github.com/torvalds/linux")
        assert owner == "torvalds"
        assert repo == "linux"
        assert error is None
    
    def test_parse_git_ssh_url(self):
        """Test parsing git@github.com URL."""
        owner, repo, error = parse_github_url("git@github.com:golang/go.git")
        assert owner == "golang"
        assert repo == "go"
        assert error is None
    
    def test_parse_with_query_params(self):
        """Test parsing URL with query parameters."""
        owner, repo, error = parse_github_url("https://github.com/django/django?tab=readme")
        assert owner == "django"
        assert repo == "django"
        assert error is None
    
    def test_parse_invalid_url(self):
        """Test parsing invalid URL."""
        owner, repo, error = parse_github_url("https://gitlab.com/user/repo")
        assert error is not None
        assert "github.com" in error.lower()
    
    def test_parse_none_url(self):
        """Test parsing None URL."""
        owner, repo, error = parse_github_url(None)
        assert error is not None


class TestEstimateHoursToFix:
    """Tests for estimate_hours_to_fix function."""
    
    def test_simple_fix(self):
        """Test estimating simple fix."""
        hours = estimate_hours_to_fix(
            lines_of_code=100,
            complexity=1.0,
            test_coverage=80.0,
            has_docs=True,
        )
        assert 5 <= hours <= 20
    
    def test_complex_fix(self):
        """Test estimating complex fix."""
        hours = estimate_hours_to_fix(
            lines_of_code=5000,
            complexity=3.5,
            test_coverage=20.0,
            has_docs=False,
        )
        assert hours > 50
    
    def test_zero_lines(self):
        """Test with zero lines of code."""
        hours = estimate_hours_to_fix(0, 1.0, 80.0, True)
        assert hours >= 0


class TestCalculateRiskScore:
    """Tests for calculate_risk_score function."""
    
    def test_all_good(self):
        """Test scoring all-good metrics."""
        metrics = {
            "commits": 100,
            "coverage": 95,
            "bus_factor": 10,
            "docs": 100,
        }
        score = calculate_risk_score(metrics)
        assert score >= 80
    
    def test_all_bad(self):
        """Test scoring all-bad metrics."""
        metrics = {
            "commits": 0,
            "coverage": 10,
            "bus_factor": 1,
            "docs": 0,
        }
        score = calculate_risk_score(metrics)
        assert score <= 30
    
    def test_custom_weights(self):
        """Test with custom weights."""
        metrics = {"a": 50, "b": 100}
        weights = {"a": 0.75, "b": 0.25}
        score = calculate_risk_score(metrics, weights)
        # (50 * 0.75 + 100 * 0.25) / 1.0 = 62.5
        assert 62 <= score <= 63


class TestDaysSince:
    """Tests for days_since function."""
    
    def test_same_day(self):
        """Test with same day."""
        today = datetime.utcnow()
        days = days_since(today)
        assert days == 0
    
    def test_past_date(self):
        """Test with past date."""
        ten_days_ago = datetime.utcnow() - timedelta(days=10)
        days = days_since(ten_days_ago)
        assert 9 <= days <= 11  # Allow 1-day variance
    
    def test_future_date(self):
        """Test with future date."""
        future = datetime.utcnow() + timedelta(days=5)
        days = days_since(future)
        assert days < 0


class TestFormatRiskLevel:
    """Tests for format_risk_level function."""
    
    def test_low_risk(self):
        """Test low risk score."""
        level = format_risk_level(85)
        assert level.lower() == "low"
    
    def test_medium_risk(self):
        """Test medium risk score."""
        level = format_risk_level(60)
        assert level.lower() == "medium"
    
    def test_high_risk(self):
        """Test high risk score."""
        level = format_risk_level(35)
        assert level.lower() == "high"
    
    def test_critical_risk(self):
        """Test critical risk score."""
        level = format_risk_level(10)
        assert level.lower() == "critical"


class TestSanitizeString:
    """Tests for sanitize_string function."""
    
    def test_truncate_long_string(self):
        """Test truncating long string."""
        long_text = "x" * 1000
        result = sanitize_string(long_text, max_length=100)
        assert len(result) <= 100
    
    def test_short_string_unchanged(self):
        """Test short string unchanged."""
        text = "Hello World"
        result = sanitize_string(text, max_length=100)
        assert result == text
    
    def test_empty_string(self):
        """Test empty string."""
        result = sanitize_string("", max_length=100)
        assert result == ""


class TestExtractVersion:
    """Tests for extract_version function."""
    
    def test_semantic_version(self):
        """Test extracting semantic version."""
        version = extract_version("1.2.3")
        assert version == "1.2.3"
    
    def test_version_with_v_prefix(self):
        """Test version with v prefix."""
        version = extract_version("v1.2.3")
        assert "1.2.3" in version or version == "1.2.3"
    
    def test_invalid_version(self):
        """Test invalid version string."""
        version = extract_version("not-a-version")
        assert version == "not-a-version"


class TestNormalizePackageName:
    """Tests for normalize_package_name function."""
    
    def test_uppercase_to_lowercase(self):
        """Test uppercase to lowercase."""
        name = normalize_package_name("NumPy")
        assert name == "numpy"
    
    def test_underscores_to_dashes(self):
        """Test underscores to dashes."""
        name = normalize_package_name("scikit_learn")
        assert name == "scikit-learn" or name == "scikitlearn"
    
    def test_already_normalized(self):
        """Test already normalized name."""
        name = normalize_package_name("requests")
        assert name == "requests"


class TestIsValidCommitHash:
    """Tests for is_valid_commit_hash function."""
    
    def test_valid_sha1_hash(self):
        """Test valid SHA1 hash (40 chars)."""
        valid = is_valid_commit_hash("abc123def456abc123def456abc123def456abc1")
        assert valid
    
    def test_valid_sha256_hash(self):
        """Test valid SHA256 hash (64 chars)."""
        valid_hash = "a" * 64
        valid = is_valid_commit_hash(valid_hash)
        assert valid
    
    def test_short_hash(self):
        """Test short hash (7 chars)."""
        valid = is_valid_commit_hash("abc1234")
        assert valid
    
    def test_invalid_hash(self):
        """Test invalid hash with non-hex characters."""
        valid = is_valid_commit_hash("not-a-valid-hash!")
        assert not valid
    
    def test_empty_hash(self):
        """Test empty hash."""
        valid = is_valid_commit_hash("")
        assert not valid


class TestCalculateAgePercentage:
    """Tests for calculate_age_percentage function."""
    
    def test_not_exceeded(self):
        """Test age not exceeding threshold."""
        percentage = calculate_age_percentage(30, 90)
        assert percentage < 1.0
    
    def test_at_threshold(self):
        """Test age at threshold."""
        percentage = calculate_age_percentage(90, 90)
        assert 0.95 <= percentage <= 1.05  # Approximately 100%
    
    def test_exceeded(self):
        """Test age exceeding threshold."""
        percentage = calculate_age_percentage(180, 90)
        assert percentage > 1.0
