"""Backward-compatibility shim for the historical ``celery_tasks`` module.

The Celery application and tasks now live in :mod:`gitrate.workers.celery_app` and
:mod:`gitrate.workers.tasks`.  The old module name is kept so existing deployment
commands (``celery -A celery_tasks worker``) keep resolving; prefer::

    celery -A gitrate.workers.celery_app:celery_app worker --loglevel=info
"""

from gitrate.workers.celery_app import celery_app
from gitrate.workers.tasks import (
    cleanup_old_audits,
    generate_pdf_report_task,
    refresh_vulnerability_cache,
    run_audit_task,
    send_audit_email_notification,
)

__all__ = [
    "celery_app",
    "cleanup_old_audits",
    "generate_pdf_report_task",
    "refresh_vulnerability_cache",
    "run_audit_task",
    "send_audit_email_notification",
]
