"""
User Pydantic schemas for request/response validation.
"""
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


def _validate_password_strength(value: str) -> str:
    """Validate password strength rules shared by auth schemas."""
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one digit")
    return value


class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class UserResponse(BaseModel):
    """Schema for returning user data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    """Schema for requesting a password reset OTP."""
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class ResetPasswordRequest(BaseModel):
    """Schema for completing a password reset with an OTP."""
    email: EmailStr
    otp: str
    new_password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("otp")
    @classmethod
    def normalize_otp(cls, value: str) -> str:
        otp = value.strip()
        if not otp.isdigit():
            raise ValueError("OTP must contain digits only")
        if len(otp) < 4 or len(otp) > 8:
            raise ValueError("OTP must be between 4 and 8 digits")
        return otp

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class DetailResponse(BaseModel):
    """Simple detail response payload."""
    detail: str
