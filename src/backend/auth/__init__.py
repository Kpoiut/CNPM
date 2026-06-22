"""
Auth module — JWT authentication + RBAC for Real Estate AVM.

Keep package import lightweight. Schema loaders and Alembic only need the model
classes; importing the router/dependencies eagerly would also import auth
service configuration and require production secrets during metadata loading.
"""

from src.backend.auth.models import RefreshToken, User, UserSession

__all__ = [
    "RefreshToken",
    "User",
    "UserSession",
    "router",
    "get_current_user",
    "require_admin",
    "get_optional_user",
]


def __getattr__(name: str):
    if name == "router":
        from src.backend.auth.router import router

        return router
    if name in {"get_current_user", "require_admin", "get_optional_user"}:
        from src.backend.auth.dependencies import (
            get_current_user,
            get_optional_user,
            require_admin,
        )

        return {
            "get_current_user": get_current_user,
            "require_admin": require_admin,
            "get_optional_user": get_optional_user,
        }[name]
    raise AttributeError(f"module 'src.backend.auth' has no attribute {name!r}")
