#!/usr/bin/env python
"""One-off, reproducible migration: move GitRate's flat top-level modules into the
``gitrate/`` package (see ``gitrate/__init__.py`` and ``docs/ARCHITECTURE.md``).

Why this exists
---------------
The repository shipped with top-level packages (``core/``, ``utils/``, ``auditors/``,
``integrations/``, ``pages/``, ``report_generators/``, ``ai_analysis/``) while
``docker-compose.yml``, ``Dockerfile.backend``, ``.github/workflows/ci-cd.yml``,
``pyproject.toml`` and CI's mypy/bandit/coverage invocations all referenced a
``gitrate`` package that did not exist.  Nothing could be built or scanned.

What it does
------------
1. ``git mv`` the modules into the canonical ``gitrate/`` package layout.
2. Rewrites the import statements inside every ``*.py`` file so they point at the
   new locations (only lines that are import statements are touched).
3. Removes the emptied legacy directories.

If a source path is missing it reports it and continues, so re-running after a
partial migration does not corrupt the tree.

Usage (from the repository root)::

    python tools/restructure_package_layout.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------------------
# 1. Moves (git mv source -> destination), executed in order
# --------------------------------------------------------------------------------------
MOVES: list[tuple[str, str]] = [
    # top level modules -> package
    ("app.py", "gitrate/main.py"),
    ("celery_tasks.py", "gitrate/workers/tasks.py"),
    ("core", "gitrate/core"),
    ("utils", "gitrate/utils"),
    ("auditors", "gitrate/auditors"),
    ("integrations", "gitrate/integrations"),
    ("pages", "gitrate/api"),
    ("report_generators", "gitrate/reports"),
    ("tests", "gitrate/tests"),
    # core/database.py -> gitrate/database/models.py (ORM + persistence helpers)
    ("gitrate/core/database.py", "gitrate/database/models.py"),
    ("migrations", "gitrate/database/migrations"),
    # auditors split by domain
    (
        "gitrate/auditors/security_auditor.py",
        "gitrate/auditors/security/security_auditor.py",
    ),
    (
        "gitrate/auditors/code_quality_auditor.py",
        "gitrate/auditors/code_quality/code_quality_auditor.py",
    ),
    (
        "gitrate/auditors/ip_legal_auditor.py",
        "gitrate/auditors/ip_legal/ip_legal_auditor.py",
    ),
    (
        "gitrate/auditors/team_sustainability_auditor.py",
        "gitrate/auditors/team/team_sustainability_auditor.py",
    ),
    # ai_analysis -> intelligence (single insight/ML architecture)
    ("ai_analysis/ml_models.py", "gitrate/intelligence/models/ml_models.py"),
    ("ai_analysis/ml_utilities.py", "gitrate/intelligence/models/ml_utilities.py"),
    (
        "ai_analysis/enhanced_insights.py",
        "gitrate/intelligence/insights/enhanced_insights.py",
    ),
    (
        "ai_analysis/insights_engine.py",
        "gitrate/intelligence/insights/insights_engine.py",
    ),
]

# --------------------------------------------------------------------------------------
# 2. Import rewrites (applied only to lines that are import statements)
# --------------------------------------------------------------------------------------
IMPORT_LINE = re.compile(r"^\s*(from\s+\.?[A-Za-z_][\w.]*\s+import\s|import\s+[A-Za-z_][\w.]*)")

RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![\w.])ai_analysis\.ml_models\b"), "gitrate.intelligence.models.ml_models"),
    (re.compile(r"(?<![\w.])ai_analysis\.ml_utilities\b"), "gitrate.intelligence.models.ml_utilities"),
    (re.compile(r"(?<![\w.])ai_analysis\.enhanced_insights\b"), "gitrate.intelligence.insights.enhanced_insights"),
    (re.compile(r"(?<![\w.])ai_analysis\.insights_engine\b"), "gitrate.intelligence.insights.insights_engine"),
    (re.compile(r"(?<![\w.])auditors\.base_auditor\b"), "gitrate.auditors.base_auditor"),
    (re.compile(r"(?<![\w.])auditors\.security_auditor\b"), "gitrate.auditors.security.security_auditor"),
    (
        re.compile(r"(?<![\w.])auditors\.code_quality_auditor\b"),
        "gitrate.auditors.code_quality.code_quality_auditor",
    ),
    (re.compile(r"(?<![\w.])auditors\.ip_legal_auditor\b"), "gitrate.auditors.ip_legal.ip_legal_auditor"),
    (
        re.compile(r"(?<![\w.])auditors\.team_sustainability_auditor\b"),
        "gitrate.auditors.team.team_sustainability_auditor",
    ),
    (re.compile(r"(?<![\w.])auditors\b"), "gitrate.auditors"),
    (re.compile(r"(?<![\w.])core\.database\b"), "gitrate.database.models"),
    (re.compile(r"(?<![\w.])core\b"), "gitrate.core"),
    (re.compile(r"(?<![\w.])utils\b"), "gitrate.utils"),
    (re.compile(r"(?<![\w.])integrations\b"), "gitrate.integrations"),
    (re.compile(r"(?<![\w.])report_generators\b"), "gitrate.reports"),
    (re.compile(r"(?<![\w.])pages\b"), "gitrate.api"),
    (re.compile(r"(?<![\w.])migrations\b"), "gitrate.database.migrations"),
    (re.compile(r"(?<![\w.])celery_tasks\b"), "gitrate.workers.tasks"),
    (re.compile(r"(?<![\w.])tests(?=\.)"), "gitrate.tests"),
    (re.compile(r"(?<![\w.])app(?=\s+import\s+app\b)"), "gitrate.main"),
]

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "venv",
    ".venv",
    "node_modules",
    "tools",
    "benchmark/benchmark_repositories",
    "evaluation/benchmark_repositories",
}


def git(*args: str) -> None:
    """Run a git command in the repository root, raising on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")


def move_all() -> list[str]:
    """Perform every move, returning the list of skipped (already migrated) paths."""
    skipped: list[str] = []
    for src, dst in MOVES:
        src_path, dst_path = ROOT / src, ROOT / dst
        if not src_path.exists():
            skipped.append(f"{src} -> {dst} (source absent; assuming already migrated)")
            continue
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if dst_path.exists():
            skipped.append(f"{src} -> {dst} (destination exists; skipped)")
            continue
        git("mv", src, dst)
    return skipped


def drop_emptied_dirs() -> list[str]:
    """Remove now-empty legacy package directories (tracked __init__ files excepted)."""
    removed: list[str] = []
    for legacy in (
        "ai_analysis",
        "core",
        "pages",
        "utils",
        "auditors",
        "integrations",
        "report_generators",
    ):
        path = ROOT / legacy
        if not path.exists():
            continue
        init = path / "__init__.py"
        if init.exists():
            git("rm", "-q", init.relative_to(ROOT).as_posix())
        shutil.rmtree(path, ignore_errors=True)
        removed.append(legacy)
    return removed


def is_skipped(path: Path) -> bool:
    """Return True when a path lives in a directory that must not be rewritten."""
    rel = path.relative_to(ROOT).as_posix()
    return any(rel == skip or rel.startswith(skip + "/") for skip in SKIP_DIRS)


def rewrite_imports() -> dict[str, int]:
    """Rewrite import statements in every Python file; return per-file change counts."""
    changed: dict[str, int] = {}
    for path in sorted(ROOT.rglob("*.py")):
        if is_skipped(path):
            continue
        original = path.read_text(encoding="utf-8")
        lines, count = original.splitlines(keepends=True), 0
        for index, line in enumerate(lines):
            if not IMPORT_LINE.match(line):
                continue
            new_line = line
            for pattern, replacement in RULES:
                new_line = pattern.sub(replacement, new_line)
            if new_line != line:
                lines[index] = new_line
                count += 1
        if count:
            path.write_text("".join(lines), encoding="utf-8")
            changed[path.relative_to(ROOT).as_posix()] = count
    return changed


def main() -> int:
    """Run the migration and print a human-readable report."""
    print(f"Repository root: {ROOT}\n")
    print("== 1. moving modules into the gitrate/ package ==")
    for entry in move_all():
        print(f"  skipped: {entry}")
    print("\n== 2. removing emptied legacy directories ==")
    for entry in drop_emptied_dirs():
        print(f"  removed: {entry}")
    print("\n== 3. rewriting imports ==")
    changed = rewrite_imports()
    for file, count in changed.items():
        print(f"  {file}: {count} import line(s)")
    print(f"\nDone: {len(changed)} file(s) rewritten.")
    print("Next: create the new subpackage __init__ files and run `python -m pytest -q`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

