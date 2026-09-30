# GitRate Documentation

This directory is the entry point for project documentation. Historical phase
reports remain in the repository root so their original links and delivery
records are preserved.

## Start Here

1. [README](../README.md) - project overview and local setup
2. [QUICKSTART](../QUICKSTART.md) - fastest development walkthrough
3. [Current project structure](PROJECT_STRUCTURE_CURRENT.md) - layout matching the current `gitrate/` package
4. [Current status](../PROJECT_COMPLETE_STATUS.md) - phase and delivery status

## Current Reference

| Topic | Document |
| --- | --- |
| Architecture | [ARCHITECTURE_VISUAL_GUIDE.md](../ARCHITECTURE_VISUAL_GUIDE.md) |
| Technology stack | [TECH_STACK.md](../TECH_STACK.md) |
| ML dashboard usage | [ML_DASHBOARD_USER_GUIDE.md](../ML_DASHBOARD_USER_GUIDE.md) |
| Testing | [TEST_QUICK_REFERENCE.md](../TEST_QUICK_REFERENCE.md) |
| Test inventory | [TEST_FILE_MANIFEST.md](../TEST_FILE_MANIFEST.md) |
| Acquisition audit plan | [ACQUISITION_AUDIT_IMPLEMENTATION_PLAN.md](../ACQUISITION_AUDIT_IMPLEMENTATION_PLAN.md) |

## Phase Reports

Phase reports are retained at the repository root and are organized by prefix:

- `PHASE_1_*` through `PHASE_8_*` contain implementation and delivery history.
- `*_SUMMARY*`, `*_COMPLETION*`, and `*_DELIVERY*` are historical snapshots,
  not the source of truth for the current package layout.
- `NEXT_STEPS.md` contains planning notes and may describe work that has since
  been completed.

Use [DOCS_INDEX.md](../DOCS_INDEX.md) for the older detailed catalog. It is
retained for backwards compatibility and should not be used as the current
status source.

## Generated and Historical Artifacts

Root-level `.ev*.txt`, `.c*.txt`, `.baseline*.txt`, and `.compile.txt` files
are execution or validation artifacts. They are intentionally kept outside
this documentation hub and should not be treated as user-facing guides.
