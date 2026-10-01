"""Asynchronous workers: Celery application and task definitions."""

from gitrate.workers.celery_app import celery_app

__all__ = ["celery_app"]
