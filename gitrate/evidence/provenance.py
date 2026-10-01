"""Provenance helpers: identifiers, timestamps and fingerprints.

Guarantees provided here:

* **Reproducibility** - every finding is stamped with :data:`ANALYSIS_VERSION` so that
  results can be tied to the exact rule set that produced them.
* **Determinism** - identifiers are content-derived (SHA-256), so re-running an audit
  over identical inputs yields identical finding/evidence ids, which makes regression
  detection and deduplication reliable.
* **No credential leakage** - :func:`secret_fingerprint` returns a truncated, salted
  digest.  Raw secret values must never be persisted or logged.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from gitrate import ANALYSIS_VERSION

__all__ = [
    "ANALYSIS_VERSION",
    "fingerprint",
    "new_finding_id",
    "secret_fingerprint",
    "utc_now",
]

# Installation salt used only for secret fingerprints.  Deliberately *not* the
# application SECRET_KEY: fingerprints must remain stable if keys are rotated.
_FINGERPRINT_SALT = os.environ.get("GITRATE_FINGERPRINT_SALT", "gitrate-evidence-v1")


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def fingerprint(*parts: str, length: int = 16) -> str:
    """Return a deterministic, truncated SHA-256 digest of the given parts."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8", errors="replace"))
    return digest.hexdigest()[:length]


def new_finding_id(category: str, title: str) -> str:
    """Build a deterministic finding identifier: ``fnd_<12 hex chars>``."""
    return f"fnd_{fingerprint(category.lower(), title.lower(), length=12)}"


def secret_fingerprint(value: str, *, length: int = 12) -> str:
    """Return a non-reversible fingerprint of a secret value.

    Only this fingerprint (never the raw secret) may be stored or reported.
    """
    salted = hashlib.sha256(f"{_FINGERPRINT_SALT}:{value}".encode("utf-8"))
    return salted.hexdigest()[:length]
