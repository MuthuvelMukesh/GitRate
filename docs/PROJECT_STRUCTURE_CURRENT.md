# Current Project Structure

This reference describes the package layout after the repository
reorganization. Paths below are relative to the repository root.

```text
gitrate/
├── api/             FastAPI routers and dashboard endpoints
├── auditors/        Audit implementations grouped by domain
├── core/            Audit engine, state, caching, queue, and webhooks
├── database/        Database session, models, and Alembic migrations
├── evidence/        Evidence collection and processing
├── integrations/    GitHub and repository integrations
├── intelligence/    ML models and insight generation
├── observability/   Logging, metrics, and monitoring support
├── reports/         Report and compliance output generation
├── security/        Authentication and security helpers
├── tests/           Unit and integration tests
├── utils/           Configuration and shared utilities
├── workers/         Celery application and background tasks
└── main.py          FastAPI application entry point
```

## Supporting Paths

| Path | Purpose |
| --- | --- |
| `docs/` | Documentation hub and current references |
| `monitoring/` | Prometheus and alerting configuration |
| `scripts/` | Database and environment helper scripts |
| `tools/` | Repository maintenance utilities |
| `gitrate/tests/` | Tests packaged with the application |

## Historical Reference

[PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) records the original scaffold
and is retained as history. It references pre-reorganization paths such as
`core/`, `pages/`, `ai_analysis/`, and `report_generators/`; use this document
when describing the current tree.
