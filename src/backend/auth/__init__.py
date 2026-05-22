"""
Auth module — JWT authentication + RBAC for Real Estate AVM.

Database tables:
    - users: User accounts with role (user/admin)
    - user_sessions: Login session tracking
    - audit_logs: All auth events logged

Exports:
    - router: FastAPI auth router
    - get_current_user, require_admin: FastAPI dependencies
    - User, UserSession: SQLAlchemy models
"""

from src.backend.auth.router import router
from src.backend.auth.dependencies import get_current_user, require_admin, get_optional_user
from src.backend.auth.models import User, UserSession

__all__ = ["router", "get_current_user", "require_admin", "get_optional_user", "User", "UserSession"]
