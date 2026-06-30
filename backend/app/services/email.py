"""
Email delivery helpers for authentication flows.
"""
import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_password_reset_otp_email(
    to_email: str,
    otp: str,
    expires_in_minutes: int,
) -> None:
    """Send a password reset OTP email using SMTP."""
    if not settings.SMTP_SENDER_EMAIL:
        raise RuntimeError("SMTP_SENDER_EMAIL is not configured.")
    if not settings.GOOGLE_APP_PASSWORD:
        raise RuntimeError("GOOGLE_APP_PASSWORD is not configured.")

    message = EmailMessage()
    message["Subject"] = f"{settings.APP_NAME} password reset OTP"
    message["From"] = settings.SMTP_SENDER_EMAIL
    message["To"] = to_email
    message.set_content(
        "\n".join(
            [
                f"Your {settings.APP_NAME} password reset OTP is: {otp}",
                "",
                f"This code will expire in {expires_in_minutes} minutes.",
                "If you did not request this reset, you can ignore this email.",
            ]
        )
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.SMTP_SENDER_EMAIL, settings.GOOGLE_APP_PASSWORD)
        smtp.send_message(message)
