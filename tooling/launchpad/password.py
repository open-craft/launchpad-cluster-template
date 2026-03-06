"""
Password management utilities for Argo installations.
"""

import secrets
import string
from datetime import datetime, timezone

import bcrypt

from launchpad.exceptions import PasswordError


def generate_password(length: int = 24) -> str:
    """
    Generate a secure random password.

    Args:
        length: Length of the password (default: 24)

    Returns:
        Generated password string
    """

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def bcrypt_password(plaintext: str, rounds: int = 10) -> str:
    """
    Bcrypt-hash a plaintext password.

    Args:
        plaintext: Plaintext password
        rounds: Bcrypt rounds (default: 10, matching shell script)

    Returns:
        Bcrypt hash string

    Raises:
        PasswordError: If bcrypt hashing fails
    """

    if not plaintext:
        raise PasswordError("Plaintext password cannot be empty")

    try:
        password_bytes = plaintext.encode("utf-8")
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")
    except Exception as e:
        raise PasswordError(f"Failed to bcrypt password: {e}") from e


def get_password_mtime() -> str:
    """
    Get an RFC3339 UTC timestamp for ArgoCD admin.passwordMtime.

    Returns:
        RFC3339 formatted timestamp string
    """

    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_plaintext_password(provided_password: str = "") -> str:
    """
    Resolve the plaintext password to use.

    If a password is provided, use it. Otherwise, generate a new secure password.

    Args:
        provided_password: Optional password provided by user

    Returns:
        Password to use (provided or generated)
    """

    if provided_password:
        return provided_password

    return generate_password()
