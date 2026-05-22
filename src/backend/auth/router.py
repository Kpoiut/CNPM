"""
Auth API endpoints — production-grade.

Every action writes to SQLite:
- Login  → users.last_login + user_sessions row + audit_logs row
- Register → users row + audit_logs row
- Seed admin → users row + audit_logs row
- Logout → user_sessions.is_revoked + audit_logs row

POST /api/auth/login       — Login → JWT + DB session
POST /api/auth/register    — Register → JWT + DB record
POST /api/auth/seed-admin  — Seed first admin (only when 0 admins)
POST /api/auth/logout      — Revoke current session
GET  /api/auth/me          — Get current user
GET  /api/auth/sessions    — Admin: list all sessions
GET  /api/auth/users       — Admin: list all users
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.backend.deps import get_db
from src.backend.auth.models import User, UserSession
from src.backend.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    SeedAdminRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
    UpdateUserRequest,
)
from src.backend.auth.service import (
    hash_password,
    verify_password,
    create_access_token,
    hash_token,
    get_token_expiry,
    log_audit,
)
from src.backend.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _build_token_response(user: User, db: Session, request: Request) -> TokenResponse:
    """Create JWT, record session in DB, return response."""
    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
    })

    # Record session in DB
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
        expires_at=get_token_expiry(),
    )
    db.add(session)

    # Update last_login
    user.last_login = datetime.utcnow()
    db.flush()

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user → JWT token + session in DB."""
    user = db.query(User).filter(User.username == body.username).first()

    if not user or not verify_password(body.password, user.hashed_password):
        # Log failed attempt
        log_audit(
            db,
            table_name="users",
            action_type="LOGIN_FAILED",
            changed_by=f"attempt:{body.username}",
            note=f"Failed login from IP {request.client.host if request.client else 'unknown'}",
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ten dang nhap hoac mat khau khong dung.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tai khoan da bi khoa.",
        )

    response = _build_token_response(user, db, request)

    # Audit log
    log_audit(
        db,
        table_name="users",
        action_type="LOGIN",
        record_id=user.id,
        changed_by=f"user:{user.username}",
        note=f"Login from IP {request.client.host if request.client else 'unknown'}",
    )
    db.commit()

    return response


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Register new user → JWT token + DB record."""
    # Duplicate check
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ten dang nhap '{body.username}' da ton tai.",
        )

    if body.email and db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email da duoc su dung.",
        )

    # Create user in DB
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()  # Get user.id

    response = _build_token_response(user, db, request)

    # Audit log
    log_audit(
        db,
        table_name="users",
        action_type="REGISTER",
        record_id=user.id,
        changed_by=f"user:{user.username}",
        new_value=json.dumps({"username": user.username, "email": user.email, "role": user.role}),
        note=f"New user registered from IP {request.client.host if request.client else 'unknown'}",
    )
    db.commit()

    return response


@router.post("/seed-admin", response_model=TokenResponse)
def seed_admin(body: SeedAdminRequest, request: Request, db: Session = Depends(get_db)):
    """Seed first admin. Only works when NO admin exists in DB."""
    existing = db.query(User).filter(User.role == "admin").first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin da ton tai. Khong the seed them.",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()

    response = _build_token_response(user, db, request)

    log_audit(
        db,
        table_name="users",
        action_type="SEED_ADMIN",
        record_id=user.id,
        changed_by="system:seed-admin",
        new_value=json.dumps({"username": user.username, "role": "admin"}),
        note="Admin account created via API seed-admin endpoint",
    )
    db.commit()

    return response


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke current session in DB."""
    # Extract token from header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_h = hash_token(token)

        # Find and revoke session
        session = db.query(UserSession).filter(
            UserSession.token_hash == token_h,
            UserSession.is_revoked == False,
        ).first()

        if session:
            session.is_revoked = True

    log_audit(
        db,
        table_name="user_sessions",
        action_type="LOGOUT",
        record_id=user.id,
        changed_by=f"user:{user.username}",
        note=f"Logout from IP {request.client.host if request.client else 'unknown'}",
    )
    db.commit()

    return MessageResponse(message="Dang xuat thanh cong.", success=True)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user info from DB."""
    return UserResponse.model_validate(user)


@router.get("/sessions")
def list_sessions(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin: list all active sessions from DB."""
    sessions = db.query(UserSession).filter(
        UserSession.is_revoked == False,
    ).order_by(UserSession.created_at.desc()).limit(100).all()

    result = []
    for s in sessions:
        u = db.query(User).filter(User.id == s.user_id).first()
        result.append({
            "id": s.id,
            "user_id": s.user_id,
            "username": u.username if u else "?",
            "role": u.role if u else "?",
            "ip_address": s.ip_address,
            "user_agent": s.user_agent[:100] if s.user_agent else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        })

    return {"sessions": result, "total": len(result)}


@router.patch("/users/{user_id}")
def update_user(
    user_id: int,
    body: UpdateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: update user role or active status."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    if body.role is not None:
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active

    log_audit(
        db,
        table_name="users",
        action_type="UPDATE_USER",
        record_id=user_id,
        changed_by=f"user:{admin.username}",
        new_value=json.dumps({"role": target.role, "is_active": target.is_active}),
        note=f"Updated by admin {admin.username} from IP {request.client.host if request.client else 'unknown'}",
    )
    db.commit()
    db.refresh(target)
    return UserResponse.model_validate(target)


@router.get("/users")
def list_users(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin: list all users from DB."""
    users = db.query(User).order_by(User.created_at.desc()).all()

    result = []
    for u in users:
        # Count sessions
        session_count = db.query(UserSession).filter(UserSession.user_id == u.id).count()
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == u.id,
            UserSession.is_revoked == False,
        ).count()

        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "total_sessions": session_count,
            "active_sessions": active_sessions,
        })

    return {"users": result, "total": len(result)}
