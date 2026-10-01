"""Backward-compatibility shim.

The canonical application entrypoint is ``gitrate.main:app``; this module is kept so
that the historically documented command ``uvicorn app:app`` keeps working.  New
deployments should use::

    uvicorn gitrate.main:app --host 0.0.0.0 --port 8000
"""

from gitrate.main import app, create_app

__all__ = ["app", "create_app"]
