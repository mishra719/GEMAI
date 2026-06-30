import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.deps import get_db
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.main import app, ensure_runtime_schema
from app.models.user import User


class AuthRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_auth_recovery.db")
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        Base.metadata.create_all(bind=self.engine)

        original_engine = ensure_runtime_schema.__globals__["engine"]
        ensure_runtime_schema.__globals__["engine"] = self.engine
        try:
            ensure_runtime_schema()
        finally:
            ensure_runtime_schema.__globals__["engine"] = original_engine

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        with self.SessionLocal() as db:
            db.add(
                User(
                    email="reset@example.com",
                    hashed_password=hash_password("Password1"),
                )
            )
            db.commit()

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_forgot_password_returns_dev_otp_when_email_is_unconfigured(self):
        with patch("app.api.auth._generate_otp", return_value="123456"):
            response = self.client.post(
                "/api/auth/forgot-password",
                json={"email": "reset@example.com"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Development OTP: 123456", response.json()["detail"])

        with self.SessionLocal() as db:
            user = db.query(User).filter(User.email == "reset@example.com").first()
            self.assertIsNotNone(user.reset_otp_hash)
            self.assertIsNotNone(user.reset_otp_expires_at)

    def test_reset_password_updates_password_and_clears_otp(self):
        with patch("app.api.auth._generate_otp", return_value="654321"):
            forgot_response = self.client.post(
                "/api/auth/forgot-password",
                json={"email": "reset@example.com"},
            )

        self.assertEqual(forgot_response.status_code, 200)

        reset_response = self.client.post(
            "/api/auth/reset-password",
            json={
                "email": "reset@example.com",
                "otp": "654321",
                "new_password": "NewPassword2",
            },
        )

        self.assertEqual(reset_response.status_code, 200)
        self.assertIn("Password updated successfully", reset_response.json()["detail"])

        with self.SessionLocal() as db:
            user = db.query(User).filter(User.email == "reset@example.com").first()
            self.assertTrue(verify_password("NewPassword2", user.hashed_password))
            self.assertIsNone(user.reset_otp_hash)
            self.assertIsNone(user.reset_otp_expires_at)
