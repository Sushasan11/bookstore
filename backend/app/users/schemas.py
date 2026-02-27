"""Pydantic request/response schemas for auth endpoints."""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """POST /auth/register request body.

    NOTE: No 'role' field — registration always creates user role.
    """

    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """POST /auth/login request body."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """POST /auth/refresh and POST /auth/logout request body."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Response for register, login, and refresh endpoints."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User info response model."""

    id: int
    email: str
    role: str

    model_config = {"from_attributes": True}
