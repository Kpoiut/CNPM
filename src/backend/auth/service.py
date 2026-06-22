"""
Auth service — JWT + password hashing + audit logging.

Production-grade: every action writes to DB.
"""

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.backend.models import AuditLog


# --- Configuration ---

_env_secret = os.getenv("JWT_SECRET_KEY")
if not _env_secret:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable is not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
SECRET_KEY = _env_secret
ALGORITHM = "HS256"
ISSUER = "real-estate-avm"
# Access token NGẮN (mặc định 120 phút); refresh token dài hơn + xoay vòng.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "14"))


# --- Password hashing ---

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


# --- JWT tokens ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with expiry + jti + issuer (defense-in-depth)."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": ISSUER,
        "typ": "access",
        "jti": uuid.uuid4().hex,
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode + validate JWT (signature, exp, issuer; algorithm pinned). None on fail."""
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"verify_aud": False, "require": ["exp", "iat"]},
        )
    except JWTError:
        return None


def create_refresh_token() -> str:
    """Random opaque refresh token (lưu DB dạng hash, có thể thu hồi + xoay vòng)."""
    return secrets.token_urlsafe(48)


def get_refresh_expiry() -> datetime:
    """Expiry datetime for a new refresh token."""
    return datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


def hash_token(token: str) -> str:
    """SHA256 hash of token for DB storage (never store raw JWT)."""
    return hashlib.sha256(token.encode()).hexdigest()


def get_token_expiry() -> datetime:
    """Get expiry datetime for a new token."""
    return datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)


# --- Audit logging ---

def log_audit(
    db: Session,
    *,
    table_name: str,
    action_type: str,
    record_id: Optional[int] = None,
    changed_by: str = "system",
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    """Write an audit log entry to the database. Commits immediately."""
    entry = AuditLog(
        record_id=record_id,
        table_name=table_name,
        action_type=action_type,
        changed_by=changed_by,
        old_value_json=old_value,
        new_value_json=new_value,
        change_note=note,
    )
    db.add(entry)
    db.flush()  # Write to DB immediately but let caller commit
