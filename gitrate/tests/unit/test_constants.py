"""Unit tests for constants."""

import pytest

from gitrate.utils.constants import (
    RiskLevel,
    DEPENDENCY_FILES,
    CI_CD_FILES,
    VIRAL_LICENSES,
    PERMISSIVE_LICENSES,
    PROPRIETARY_LICENSES,
    RISK_THRESHOLDS,
    BUS_FACTOR_CRITICAL,
    BUS_FACTOR_HIGH,
    BUS_FACTOR_MEDIUM,
    TEST_COVERAGE_TARGET,
    CVE_AGE_CRITICAL_DAYS,
    DEBT_ESTIMATION,
)


class TestRiskLevelEnum:
    """Tests for RiskLevel enum."""
    
    def test_risk_levels_exist(self):
        """Test all risk level values exist."""
        levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(levels) == 4
    
    def test_risk_level_string_value(self):
        """Test risk level string values."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.HIGH.value == "HIGH"


class TestDependencyFiles:
    """Tests for DEPENDENCY_FILES constant."""
    
    def test_dependency_files_populated(self):
        """Test DEPENDENCY_FILES is populated."""
        assert len(DEPENDENCY_FILES) > 0
    
    def test_python_dependencies(self):
        """Test Python dependency files."""
        assert "python" in DEPENDENCY_FILES
        python_files = DEPENDENCY_FILES["python"]
        assert "requirements.txt" in python_files
    
    def test_javascript_dependencies(self):
        """Test JavaScript dependency files."""
        assert "javascript" in DEPENDENCY_FILES
        js_files = DEPENDENCY_FILES["javascript"]
        assert "package.json" in js_files
    
    def test_all_file_lists_are_lists(self):
        """Test all dependency file lists are lists."""
        for lang, files in DEPENDENCY_FILES.items():
            assert isinstance(files, list)
            assert len(files) > 0


class TestCICDFiles:
    """Tests for CI_CD_FILES constant."""
    
    def test_ci_cd_files_populated(self):
        """Test CI_CD_FILES is populated."""
        assert len(CI_CD_FILES) > 0
    
    def test_github_actions(self):
        """Test GitHub Actions detection."""
        assert "github" in CI_CD_FILES
    
    def test_all_platforms_have_patterns(self):
        """Test all CI/CD platforms have patterns."""
        for platform, patterns in CI_CD_FILES.items():
            assert isinstance(patterns, list)
            assert len(patterns) > 0


class TestLicenseConstants:
    """Tests for license classification constants."""
    
    def test_viral_licenses(self):
        """Test viral licenses are present."""
        assert len(VIRAL_LICENSES) > 0
        assert "GPL" in VIRAL_LICENSES or any("GPL" in l for l in VIRAL_LICENSES)
    
    def test_permissive_licenses(self):
        """Test permissive licenses are present."""
        assert len(PERMISSIVE_LICENSES) > 0
        assert "MIT" in PERMISSIVE_LICENSES or any("MIT" in l for l in PERMISSIVE_LICENSES)
    
    def test_no_license_overlap(self):
        """Test no licenses in multiple categories."""
        viral_set = set(VIRAL_LICENSES)
        permissive_set = set(PERMISSIVE_LICENSES)
        proprietary_set = set(PROPRIETARY_LICENSES)
        
        # Check no overlap
        assert len(viral_set & permissive_set) == 0
        assert len(viral_set & proprietary_set) == 0
        assert len(permissive_set & proprietary_set) == 0


class TestRiskThresholds:
    """Tests for RISK_THRESHOLDS constant."""
    
    def test_thresholds_populated(self):
        """Test RISK_THRESHOLDS is populated."""
        assert len(RISK_THRESHOLDS) > 0
    
    def test_all_audit_categories_have_thresholds(self):
        """Test all audit categories have thresholds."""
        categories = ["ip_legal", "team_sustainability", "code_quality", "security"]
        for category in categories:
            assert category in RISK_THRESHOLDS
    
    def test_threshold_structure(self):
        """Test threshold structure."""
        for category, thresholds in RISK_THRESHOLDS.items():
            assert isinstance(thresholds, dict)
            # Each should have low, medium, high, critical thresholds
            for level in ["critical", "high", "medium", "low"]:
                assert level in thresholds


class TestBusFactorConstants:
    """Tests for bus factor constants."""
    
    def test_bus_factor_ordering(self):
        """Test bus factor thresholds are in correct order."""
        assert BUS_FACTOR_CRITICAL < BUS_FACTOR_HIGH
        assert BUS_FACTOR_HIGH < BUS_FACTOR_MEDIUM
    
    def test_bus_factor_values_reasonable(self):
        """Test bus factor values are reasonable."""
        assert BUS_FACTOR_CRITICAL >= 1
        assert BUS_FACTOR_CRITICAL <= 3
        assert BUS_FACTOR_MEDIUM <= 10


class TestCodeQualityConstants:
    """Tests for code quality constants."""
    
    def test_test_coverage_target(self):
        """Test test coverage target is reasonable."""
        assert 0 < TEST_COVERAGE_TARGET < 100
        assert TEST_COVERAGE_TARGET >= 70  # Reasonable minimum


class TestCVEConstants:
    """Tests for CVE aging constants."""
    
    def test_cve_aging_thresholds(self):
        """Test CVE aging thresholds."""
        assert CVE_AGE_CRITICAL_DAYS > 0
        assert CVE_AGE_CRITICAL_DAYS < 365  # Within a year


class TestDebtEstimationConstants:
    """Tests for technical debt estimation constants."""
    
    def test_debt_estimation_populated(self):
        """Test DEBT_ESTIMATION is populated."""
        assert len(DEBT_ESTIMATION) > 0
    
    def test_all_debt_items_have_hours(self):
        """Test all debt estimation items have hours."""
        for item, hours in DEBT_ESTIMATION.items():
            assert isinstance(hours, (int, float))
            assert hours > 0
    
    def test_reasonable_hour_estimates(self):
        """Test hour estimates are reasonable."""
        for item, hours in DEBT_ESTIMATION.items():
            assert hours < 1000  # No single task should take 1000+ hours
            assert hours >= 1    # Minimum 1 hour


class TestConstantDataIntegrity:
    """Tests for overall constant data integrity."""
    
    def test_no_duplicate_dependency_files(self):
        """Test no duplicate entries in dependency files."""
        for lang, files in DEPENDENCY_FILES.items():
            assert len(files) == len(set(files))
    
    def test_no_duplicate_ci_platforms(self):
        """Test no duplicate CI/CD platforms."""
        platforms = list(CI_CD_FILES.keys())
        assert len(platforms) == len(set(platforms))
    
    def test_constants_are_immutable_types(self):
        """Test constants use immutable types where appropriate."""
        # Sets should be used for membership testing
        assert isinstance(VIRAL_LICENSES, (set, frozenset, list, tuple))
        assert isinstance(PERMISSIVE_LICENSES, (set, frozenset, list, tuple))
