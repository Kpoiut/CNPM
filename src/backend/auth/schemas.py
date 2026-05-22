"""Auth request/response schemas — Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# --- Request schemas ---

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class SeedAdminRequest(BaseModel):
    username: str = Field(default="admin", min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = None


# --- Response schemas ---

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class UpdateUserRequest(BaseModel):
    role: Optional[str] = Field(None, pattern="^(user|admin)$")
    is_active: Optional[bool] = None
