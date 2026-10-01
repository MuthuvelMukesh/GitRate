"""Detector profiles for credential-like content.

Shared by the working-tree secret scanner and the historical secret scanner so both
use exactly the same definitions (single source of truth).

Only *patterns* live here.  Matched values are never returned: callers convert them
to a keyed fingerprint via :func:`gitrate.evidence.provenance.secret_fingerprint`.
"""

from __future__ import annotations

import re

# (name, compiled pattern) - ordered from most specific to most generic.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("aws_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    (
        "aws_secret_access_key",
        re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"),
    ),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("stripe_key", re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    (
        "generic_api_key",
        re.compile(r"(?i)\b(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\b\s*[:=]\s*"
                   r"['\"]([A-Za-z0-9_\-]{16,})['\"]"),
    ),
    (
        "password_literal",
        re.compile(r"(?i)\bpassword\b\s*[:=]\s*['\"]([^'\"]{8,})['\"]"),
    ),
    ("basic_auth_url", re.compile(r"https?://[^\s:@/]+:[^\s:@/]{6,}@[^\s/]+")),
]

# Files whose contents are binary/generated and must not be pattern-scanned.
BINARY_SUFFIXES: frozenset[str] = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".tar", ".whl",
        ".so", ".dll", ".exe", ".pyc", ".woff", ".woff2", ".ttf", ".mp4", ".mov",
        ".xlsx", ".docx", ".parquet", ".bin", ".jar",
    }
)

# Paths excluded from scanning: vendored/generated content produces noise, not findings.
EXCLUDED_PATH_PARTS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "vendor",
        "third_party",
        "dist",
        "build",
        "__pycache__",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
    }
)

# Placeholders that must NOT be reported as secrets (avoids obvious false positives).
PLACEHOLDER_VALUES: tuple[str, ...] = (
    "changeme",
    "change-me",
    "your-secret-key",
    "your_api_key",
    "your-api-key",
    "example",
    "placeholder",
    "dummy",
    "xxxx",
    "***",
    "test",
)
