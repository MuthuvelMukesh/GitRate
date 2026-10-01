"""Security package: authentication, authorization and hardening primitives.

Nothing in this package should be considered a security *guarantee*; see
``docs/SECURITY_ASSESSMENT.md`` for tested behaviour and residual limitations.
"""

from gitrate.security.config_validation import (
    InsecureConfigurationError,
    validate_settings,
)
from gitrate.security.rbac import Permission, Role, role_permissions
from gitrate.security.ssrf import SSRFError, validate_repository_url

__all__ = [
    "InsecureConfigurationError",
    "Permission",
    "Role",
    "SSRFError",
    "role_permissions",
    "validate_repository_url",
    "validate_settings",
]
