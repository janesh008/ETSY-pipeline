"""Tests for craftdesk_api auth endpoints."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from craftdesk_api.main import app
from craftdesk_api.db.base import get_db
from craftdesk_api.core.security import (
    encrypt,
    decrypt,
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


# ── Security unit tests (no DB needed) ───────────────────────────────────────

class TestFernetEncryption:
    """AES-256 Fernet encrypt/decrypt round-trip."""

    def test_roundtrip(self) -> None:
        plaintext = "super-secret-etsy-token-abc123"
        ciphertext = encrypt(plaintext)
        assert ciphertext != plaintext
        assert decrypt(ciphertext) == plaintext

    def test_different_ciphertexts(self) -> None:
        """Two encryptions of the same plaintext must produce different ciphertexts (Fernet uses random IV)."""
        secret = "same-value"
        c1 = encrypt(secret)
        c2 = encrypt(secret)
        assert c1 != c2
        assert decrypt(c1) == decrypt(c2) == secret


class TestBcrypt:
    """bcrypt password hashing."""

    def test_hash_verify(self) -> None:
        password = "MySecureP@ssw0rd!"
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_hash_is_not_plaintext(self) -> None:
        pw = "plaintext"
        assert hash_password(pw) != pw


class TestJWT:
    """JWT access token creation and decoding."""

    def test_access_token_roundtrip(self) -> None:
        user_id = "abc-123-uuid"
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_invalid_token_raises(self) -> None:
        from jose import JWTError
        with pytest.raises(JWTError):
            decode_token("not.a.valid.token")


# ── API endpoint tests (in-memory SQLite) ────────────────────────────────────




class TestRegisterEndpoint:

    def test_register_success(self, client) -> None:
        resp = client.post("/api/v1/auth/register", json={
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SecurePass1!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "jane@example.com"
        assert "user_id" in data

    def test_register_duplicate_email(self, client) -> None:
        payload = {"full_name": "A", "email": "dup@example.com", "password": "SecurePass1!"}
        client.post("/api/v1/auth/register", json=payload)
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_short_password(self, client) -> None:
        resp = client.post("/api/v1/auth/register", json={
            "full_name": "B",
            "email": "b@example.com",
            "password": "short",
        })
        assert resp.status_code == 422


class TestLoginEndpoint:

    def test_login_success(self, client) -> None:
        client.post("/api/v1/auth/register", json={
            "full_name": "Login User",
            "email": "login@example.com",
            "password": "GoodPassword1!",
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "login@example.com",
            "password": "GoodPassword1!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client) -> None:
        client.post("/api/v1/auth/register", json={
            "full_name": "X",
            "email": "x@example.com",
            "password": "CorrectPass1!",
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "x@example.com",
            "password": "WrongPass1!",
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client) -> None:
        resp = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "AnyPass1!",
        })
        assert resp.status_code == 401


class TestRefreshEndpoint:

    def test_refresh_success(self, client) -> None:
        client.post("/api/v1/auth/register", json={
            "full_name": "Refresh User",
            "email": "refresh@example.com",
            "password": "RefreshPass1!",
        })
        login = client.post("/api/v1/auth/login", json={
            "email": "refresh@example.com",
            "password": "RefreshPass1!",
        }).json()

        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": login["refresh_token"],
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_with_access_token_fails(self, client) -> None:
        client.post("/api/v1/auth/register", json={
            "full_name": "Y",
            "email": "y@example.com",
            "password": "YPass1234!",
        })
        login = client.post("/api/v1/auth/login", json={
            "email": "y@example.com",
            "password": "YPass1234!",
        }).json()

        # Passing the access token (type=access) as refresh should be rejected
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": login["access_token"],
        })
        assert resp.status_code == 401


class TestHealthEndpoint:

    def test_health(self, client) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
