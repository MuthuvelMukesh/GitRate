#!/usr/bin/env python
"""Test runner script: quality gates + test suite + coverage.

Usage:
    python run_tests.py            # tests + coverage
    python run_tests.py --quality  # additionally run ruff/black/mypy/bandit gates
"""

import subprocess
import sys
from pathlib import Path

# Coverage targets: the *real* package (previously targeted the non-existent
# top-level modules core/integrations/utils - see docs/IMPLEMENTATION_GAP_ANALYSIS.md).
COVERAGE_TARGETS = ["gitrate.core", "gitrate.auditors", "gitrate.evidence", "gitrate.intelligence", "gitrate.reports"]
QUALITY_GATES = [
    (["ruff", "check", "."], "Ruff lint"),
    (["black", "--check", "."], "Black formatting"),
    (["mypy", "gitrate"], "MyPy type check"),
    (["bandit", "-r", "gitrate", "-ll"], "Bandit security scan"),
]


def run_command(cmd: list, description: str) -> int:
    """Run a command and return the exit code."""
    print(f"\n{'=' * 70}")
    print(f">> {description}")
    print(f"{'=' * 70}")
    print(f"Command: {' '.join(cmd)}\n")
    return subprocess.run(cmd).returncode


def main() -> int:
    """Run the test suite, coverage and (optionally) the quality gates."""
    run_quality = "--quality" in sys.argv

    print("\n" + "=" * 70)
    print("GitRate Technical Due-Diligence Platform - Test Suite Runner")
    print("=" * 70)

    exitcode = run_command(["python", "-m", "pytest", "-q"], "Running all tests")
    if exitcode != 0:
        print("\nTests failed - see output above.")
        return exitcode

    cov_args = [f"--cov={target}" for target in COVERAGE_TARGETS]
    coverage_code = run_command(
        ["python", "-m", "pytest", "-q", *cov_args, "--cov-report=term-missing"],
        "Running tests with coverage analysis",
    )

    test_files = sorted(Path("gitrate/tests").rglob("test_*.py"))
    print(f"\nTest files: {len(test_files)}")
    for path in test_files:
        print(f"   - {path}")

    if run_quality:
        for cmd, description in QUALITY_GATES:
            code = run_command(cmd, description)
            if code != 0:
                print(f"\nQuality gate failed: {description}")
                return code

    print("\n" + "=" * 70)
    print("Test suite complete (coverage report: htmlcov/index.html)")
    print("=" * 70)
    return coverage_code


if __name__ == "__main__":
    sys.exit(main())

