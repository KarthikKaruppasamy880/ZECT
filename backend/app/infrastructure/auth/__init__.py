from app.infrastructure.auth.deps import CurrentUser, get_current_user, get_optional_user
from app.infrastructure.auth.rbac import (
    require_role,
    require_authentication,
    log_audit,
    can_user_access_resource,
    get_user_from_current_user,
    PermissionDenied,
    RequiresAuthentication,
)

__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_optional_user",
    "require_role",
    "require_authentication",
    "log_audit",
    "can_user_access_resource",
    "get_user_from_current_user",
    "PermissionDenied",
    "RequiresAuthentication",
]
