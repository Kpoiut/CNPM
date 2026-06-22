"""
Auth API endpoints — production-grade.

Every action writes to PostgreSQL:
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
import base64
import hashlib
import hmac
import os
import re
import secrets
import time
import threading
from datetime import datetime
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.backend.deps import get_db
from src.backend.config import limiter
from src.backend.auth.models import User, UserSession, RefreshToken
from src.backend.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
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
    create_refresh_token,
    hash_token,
    get_token_expiry,
    get_refresh_expiry,
    log_audit,
)
from src.backend.auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# --- Brute-force lockout (in-memory, theo username; reset khi restart) ---
_LOCK_THRESHOLD = 5          # số lần sai liên tiếp
_LOCK_WINDOW = 15 * 60       # cửa sổ tính (giây)
_LOCK_DURATION = 15 * 60     # thời gian khóa (giây)
_fail_state: dict = {}       # username -> {"count": int, "first": ts, "until": ts}
_fail_lock = threading.Lock()
_OAUTH_STATE_TTL_SECONDS = 10 * 60
_OAUTH_STATE_COOKIE = "avm_google_oauth_state"
_OAUTH_VERIFIER_COOKIE = "avm_google_oauth_verifier"


def _is_secure_request(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"


def _oauth_cookie_options(request: Request) -> dict:
    return {
        "httponly": True,
        "secure": _is_secure_request(request),
        "samesite": "lax",
        "max_age": _OAUTH_STATE_TTL_SECONDS,
        "path": "/api/auth",
    }


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _pkce_challenge(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


def _safe_frontend_redirect(value: str, request: Request) -> str:
    target = (value or "/").strip() or "/"
    parsed = urlparse(target)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return "/"
    if not parsed.netloc:
        return target if target.startswith("/") else "/"

    allowed = {
        item.strip().rstrip("/")
        for item in os.getenv("GOOGLE_OAUTH_ALLOWED_REDIRECT_ORIGINS", "").split(",")
        if item.strip()
    }
    if not allowed:
        # Server-side env controls this redirect. Without an explicit allowlist,
        # still reject non-http(s) schemes above and keep the configured origin.
        return target

    origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    request_origin = f"{request.url.scheme}://{request.url.netloc}".rstrip("/")
    if origin in allowed or origin == request_origin:
        return target
    return "/"


def _frontend_origin_from_request(request: Request) -> str | None:
    for header_name in ("origin", "referer"):
        raw = request.headers.get(header_name, "").strip()
        if not raw:
            continue
        parsed = urlparse(raw)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return None


def _local_frontend_callback(request: Request, redirect_uri: str) -> str:
    """Prefer the frontend OAuth relay when local preview started the flow."""
    parsed = urlparse(redirect_uri)
    if not (
        parsed.scheme in {"http", "https"}
        and parsed.netloc.endswith(":8000")
        and parsed.path.endswith("/api/auth/google/callback")
    ):
        return redirect_uri

    frontend_origin = _frontend_origin_from_request(request)
    if frontend_origin and frontend_origin.endswith((":4173", ":5173")):
        return f"{frontend_origin}/signin-google"

    return redirect_uri


def _google_oauth_config(request: Request) -> dict:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
    if not redirect_uri:
        redirect_uri = str(request.url_for("google_oauth_callback"))
    redirect_uri = _local_frontend_callback(request, redirect_uri)
    frontend_redirect = _safe_frontend_redirect(os.getenv("GOOGLE_OAUTH_FRONTEND_REDIRECT", "/"), request)
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "frontend_redirect": frontend_redirect,
    }


def _require_google_oauth_config(request: Request) -> dict:
    cfg = _google_oauth_config(request)
    env_names = {
        "client_id": "GOOGLE_OAUTH_CLIENT_ID",
        "client_secret": "GOOGLE_OAUTH_CLIENT_SECRET",
        "redirect_uri": "GOOGLE_OAUTH_REDIRECT_URI",
    }
    missing = [env_names[key] for key in ("client_id", "client_secret", "redirect_uri") if not cfg[key]]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Google OAuth is not configured. Missing env: {', '.join(missing)}.",
        )
    return cfg


def _safe_google_username(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    slug = re.sub(r"[^a-z0-9_]+", "_", local).strip("_") or "google_user"
    return f"google_{slug}"[:80]


def _find_or_create_google_user(db: Session, *, email: str, name: str | None) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user

    base_username = _safe_google_username(email)
    username = base_username
    suffix = 2
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}_{suffix}"[:100]
        suffix += 1

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(secrets.token_urlsafe(48)),
        role="user",
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_audit(
        db,
        table_name="users",
        action_type="GOOGLE_OAUTH_REGISTER",
        record_id=user.id,
        changed_by=f"google:{email}",
        new_value=json.dumps({"username": username, "email": email, "name": name}, ensure_ascii=False),
        note="User provisioned through Google OAuth 2.0",
    )
    return user


def _is_locked(username: str) -> int:
    """Trả về số giây còn bị khóa (0 nếu không khóa)."""
    with _fail_lock:
        st = _fail_state.get(username)
        if st and st.get("until", 0) > time.time():
            return int(st["until"] - time.time())
    return 0


def _record_fail(username: str) -> None:
    now = time.time()
    with _fail_lock:
        st = _fail_state.get(username)
        if not st or now - st.get("first", now) > _LOCK_WINDOW:
            st = {"count": 0, "first": now, "until": 0}
        st["count"] += 1
        if st["count"] >= _LOCK_THRESHOLD:
            st["until"] = now + _LOCK_DURATION
            st["count"] = 0
            st["first"] = now
        _fail_state[username] = st


def _clear_fail(username: str) -> None:
    with _fail_lock:
        _fail_state.pop(username, None)


@router.get("/google/start")
def google_oauth_start(request: Request):
    """Start Google OAuth 2.0 authorization-code login flow."""
    cfg = _require_google_oauth_config(request)
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": _pkce_challenge(verifier),
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "select_account",
    }
    response = RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")
    response.set_cookie(_OAUTH_STATE_COOKIE, state, **_oauth_cookie_options(request))
    response.set_cookie(_OAUTH_VERIFIER_COOKIE, verifier, **_oauth_cookie_options(request))
    return response


@router.get("/google/callback", name="google_oauth_callback")
def google_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """Google OAuth callback: exchange code, upsert local user, issue AVM JWT."""
    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Google OAuth failed: {error}")
    cookie_state = request.cookies.get(_OAUTH_STATE_COOKIE, "")
    verifier = request.cookies.get(_OAUTH_VERIFIER_COOKIE, "")
    if not code or not state or not cookie_state or not verifier or not hmac.compare_digest(state, cookie_state):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google OAuth state is invalid or expired.")

    cfg = _require_google_oauth_config(request)
    try:
        token_res = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "redirect_uri": cfg["redirect_uri"],
                "grant_type": "authorization_code",
                "code_verifier": verifier,
            },
            timeout=10,
        )
        token_res.raise_for_status()
        google_access_token = token_res.json().get("access_token")
        if not google_access_token:
            raise ValueError("Google token response did not include access_token")

        userinfo_res = httpx.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"},
            timeout=10,
        )
        userinfo_res.raise_for_status()
        profile = userinfo_res.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not complete Google OAuth exchange: {exc}",
        ) from exc

    email = (profile.get("email") or "").strip().lower()
    if not email or profile.get("email_verified") is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google email is missing or not verified.")

    user = _find_or_create_google_user(db, email=email, name=profile.get("name"))
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tai khoan da bi khoa.")

    response = _build_token_response(user, db, request)
    log_audit(
        db,
        table_name="users",
        action_type="GOOGLE_OAUTH_LOGIN",
        record_id=user.id,
        changed_by=f"user:{user.username}",
        note=f"Google OAuth login from IP {request.client.host if request.client else 'unknown'}",
    )
    db.commit()

    payload = response.model_dump(mode="json")
    redirect_to = cfg["frontend_redirect"] or "/"
    html = f"""<!doctype html>
<html lang="vi">
<head><meta charset="utf-8"><title>Google OAuth</title></head>
<body>
<script>
const payload = {json.dumps(payload)};
localStorage.setItem('avm-token', payload.access_token);
if (payload.refresh_token) localStorage.setItem('avm-refresh', payload.refresh_token);
localStorage.setItem('avm-user', JSON.stringify(payload.user));
window.location.replace({json.dumps(redirect_to)});
</script>
<p>Đăng nhập Google thành công. Đang chuyển hướng...</p>
</body>
</html>"""
    html_response = HTMLResponse(html)
    html_response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/auth")
    html_response.delete_cookie(_OAUTH_VERIFIER_COOKIE, path="/api/auth")
    return html_response


def _build_token_response(user: User, db: Session, request: Request) -> TokenResponse:
    """Create access JWT + opaque refresh token, record both in DB, return response."""
    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
    })

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:500]

    # Record access session in DB (cho phép thu hồi)
    db.add(UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        ip_address=ip,
        user_agent=ua,
        expires_at=get_token_expiry(),
    ))

    # Refresh token (opaque, lưu hash, xoay vòng)
    refresh = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh),
        ip_address=ip,
        user_agent=ua,
        expires_at=get_refresh_expiry(),
    ))

    # Update last_login
    user.last_login = datetime.utcnow()
    db.flush()

    return TokenResponse(
        access_token=token,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("8/minute")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Authenticate user → JWT token + session in DB. Có rate-limit + khóa brute-force."""
    uname = (body.username or "").strip().lower()
    locked = _is_locked(uname)
    if locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Đăng nhập sai quá nhiều lần. Thử lại sau {locked // 60 + 1} phút.",
        )

    user = db.query(User).filter(User.username == body.username).first()

    if not user or not verify_password(body.password, user.hashed_password):
        _record_fail(uname)
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

    _clear_fail(uname)
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


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    """Đổi refresh token lấy access token mới + XOAY VÒNG refresh (revoke cái cũ)."""
    th = hash_token(body.refresh_token)
    rt = db.query(RefreshToken).filter(
        RefreshToken.token_hash == th,
        RefreshToken.is_revoked == False,
    ).first()

    if not rt or (rt.expires_at and rt.expires_at < datetime.utcnow()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.",
        )

    user = db.query(User).filter(User.id == rt.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không khả dụng.")

    # Xoay vòng: thu hồi refresh cũ rồi cấp cặp token mới
    rt.is_revoked = True
    response = _build_token_response(user, db, request)
    db.commit()
    return response


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke current access session + tất cả refresh token của user."""
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

    # Thu hồi toàn bộ refresh token đang sống của user
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False,
    ).update({RefreshToken.is_revoked: True})

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
