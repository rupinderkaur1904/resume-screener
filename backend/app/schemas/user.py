"""
Pydantic schemas for auth and user data.

RegisterRequest / LoginRequest are what the client sends in.
UserResponse is the safe, public shape of a user - no password hash, ever.
TokenResponse is what /auth/login returns.
"""
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, v: str) -> str:
        # bcrypt silently truncates anything past 72 bytes - reject it up front
        # instead of letting two different long passwords hash identically.
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 bytes.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # builds directly from a User ORM row

    id: int
    email: str
    full_name: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
