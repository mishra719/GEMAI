"""
Authentication API endpoints: Register and Login.
"""
import logging
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_otp,
    hash_password,
    verify_otp,
    verify_password,
)
from app.models.user import User
from app.schemas.user import (
    DetailResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.email import send_password_reset_otp_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _generate_otp() -> str:
    """Generate a numeric OTP code."""
    digits = "".join(
        random.SystemRandom().choice("0123456789")
        for _ in range(settings.OTP_LENGTH)
    )
    return digits


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account."""
    # Check if email already exists
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Create user
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        ) from None
    db.refresh(user)

    logger.info(f"New user registered: {user.email}")

    # Generate token
    token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT token."""
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    logger.info(f"User logged in: {user.email}")

    token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/forgot-password", response_model=DetailResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Generate and send an OTP for password recovery."""
    generic_detail = "If that email exists, an OTP has been sent to your inbox."
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        return DetailResponse(detail=generic_detail)

    otp = _generate_otp()
    user.reset_otp_hash = hash_otp(otp)
    user.reset_otp_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.OTP_EXPIRY_MINUTES
    )
    db.commit()

    try:
        send_password_reset_otp_email(
            to_email=user.email,
            otp=otp,
            expires_in_minutes=settings.OTP_EXPIRY_MINUTES,
        )
        logger.info("Password reset OTP sent to %s", user.email)
        return DetailResponse(detail=generic_detail)
    except Exception as exc:
        logger.warning("OTP email delivery failed for %s: %s", user.email, exc)
        if settings.DEBUG:
            return DetailResponse(
                detail=(
                    f"Email delivery is not configured. Development OTP: {otp} "
                    f"(valid for {settings.OTP_EXPIRY_MINUTES} minutes)"
                )
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send OTP email right now. Please try again later.",
        ) from exc


@router.post("/reset-password", response_model=DetailResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset a user's password with a valid OTP."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.reset_otp_hash or not user.reset_otp_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or OTP",
        )

    now = datetime.now(timezone.utc)
    expires_at = user.reset_otp_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        user.reset_otp_hash = None
        user.reset_otp_expires_at = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one.",
        )

    if not verify_otp(payload.otp, user.reset_otp_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or OTP",
        )

    user.hashed_password = hash_password(payload.new_password)
    user.reset_otp_hash = None
    user.reset_otp_expires_at = None
    db.commit()

    logger.info("Password reset completed for %s", user.email)
    return DetailResponse(detail="Password updated successfully. You can sign in now.")
