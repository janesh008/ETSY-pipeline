"""CraftDesk API — security utilities: Fernet encryption, bcrypt hashing, JWT tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from craftdesk_api.core.config import settings

# ── Fernet (AES-256-CBC + HMAC-SHA256) ──────────────────────────────────────
_fernet = Fernet(settings.fernet_key.encode())


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string with AES-256 (Fernet).

    Returns a base64-encoded ciphertext string safe for database storage.
    """
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted ciphertext string back to plaintext."""
    return _fernet.decrypt(ciphertext.encode()).decode()


# ── bcrypt password hashing ──────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (cost factor 12).

    Returns a UTF-8 string suitable for the `password_hash` column.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if `plain` matches the stored `hashed` bcrypt digest."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT ──────────────────────────────────────────────────────────────────────

def _create_token(data: dict[str, object], expires_delta: timedelta) -> str:
    """Internal: encode a JWT with the given payload and expiry."""
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    """Create a short-lived JWT access token for the given user UUID."""
    return _create_token(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived JWT refresh token for the given user UUID."""
    return _create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str) -> dict[str, object]:
    """Decode and verify a JWT. Raises JWTError on invalid/expired tokens."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


__all__ = [
    "encrypt",
    "decrypt",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "JWTError",
]
