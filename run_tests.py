#!/usr/bin/env python
"""Test runner script with coverage reporting."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> int:
    """Run a command and return the exit code."""
    print(f"\n{'=' * 70}")
    print(f"▶ {description}")
    print(f"{'=' * 70}")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Run test suite with coverage."""
    test_dir = Path(__file__).parent
    
    print("\n" + "=" * 70)
    print("GitRate Acquisition Audit - Test Suite Runner")
    print("=" * 70)
    
    # 1. Run all tests
    exitcode = run_command(
        ["pytest", "tests/", "-v", "--tb=short"],
        "Running all tests"
    )
    
    if exitcode != 0:
        print("\n❌ Tests failed!")
        return exitcode
    
    print("\n✅ All tests passed!")
    
    # 2. Run with coverage
    exitcode = run_command(
        ["pytest", "tests/", "-v", "--cov=core", "--cov=integrations", 
         "--cov=utils", "--cov-report=html", "--cov-report=term-missing"],
        "Running tests with coverage analysis"
    )
    
    # 3. Show test summary
    print("\n" + "=" * 70)
    print("Test Execution Summary")
    print("=" * 70)
    
    # Count test files
    test_files = list(Path("tests").rglob("test_*.py"))
    print(f"\n📊 Test Files: {len(test_files)}")
    for f in sorted(test_files):
        print(f"   - {f.relative_to(Path.cwd())}")
    
    # Show coverage report location
    print(f"\n📈 Coverage Report: htmlcov/index.html")
    
    print("\n" + "=" * 70)
    print("✅ Test Suite Complete")
    print("=" * 70)
    
    return exitcode


if __name__ == "__main__":
    sys.exit(main())
