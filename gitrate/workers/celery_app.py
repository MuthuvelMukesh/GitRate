"""Celery application definition.

Celery is an *optional* dependency: the API runs without it (audits execute in the
in-process task queue or synchronously).  When Celery is not installed,
``celery_app`` is ``None`` and ``celery_available()`` returns ``False`` so callers
can degrade explicitly instead of crashing at import time.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from gitrate.utils.config import settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised by the import test with/without celery installed
    from celery import Celery

    CELERY_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover - dependency must be declared to use workers
    Celery = None  # type: ignore[assignment]
    CELERY_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


def celery_available() -> bool:
    """Return True when the Celery package is importable."""
    return Celery is not None


def create_celery_app() -> Optional[Any]:
    """Create the Celery application, or return ``None`` when Celery is unavailable."""
    if Celery is None:
        logger.warning(
            "Celery is not installed (%s); asynchronous worker mode is unavailable. "
            "Install workers with `pip install celery[redis]`.",
            CELERY_IMPORT_ERROR,
        )
        return None

    app = Celery(
        "gitrate",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_acks_on_failure_or_timeout=False,
    )
    return app


celery_app = create_celery_app()
