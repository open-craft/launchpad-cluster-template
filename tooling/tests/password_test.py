"""
Unit tests for the password utility functions.
"""

import string
from datetime import datetime, timezone
from unittest import mock

import bcrypt
import pytest

from launchpad.exceptions import PasswordError
from launchpad.password import (
    bcrypt_password,
    generate_password,
    get_password_mtime,
    resolve_plaintext_password,
)


class TestGeneratePassword:
    """
    Test suite for generate_password function.
    """

    def test_generate_password_default_length(self):
        """
        Test password generation with default length.
        """

        password = generate_password()

        assert isinstance(password, str)
        assert len(password) == 24
        assert all(
            c in string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
            for c in password
        )

    def test_generate_password_custom_length(self):
        """
        Test password generation with custom length.
        """

        password = generate_password(12)

        assert isinstance(password, str)
        assert len(password) == 12
        assert all(
            c in string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
            for c in password
        )

    def test_generate_password_zero_length(self):
        """
        Test password generation with zero length.
        """

        password = generate_password(0)

        assert isinstance(password, str)
        assert len(password) == 0

    def test_generate_password_uses_secure_random(self):
        """
        Test that password generation uses secure random (not predictable).
        """

        passwords = [generate_password() for _ in range(10)]
        assert len(set(passwords)) == 10

    def test_generate_password_character_set(self):
        """
        Test that password uses the correct character set.
        """

        password = generate_password(100)

        expected_chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"

        for char in password:
            assert char in expected_chars

    def test_generate_password_contains_various_char_types(self):
        """
        Test that password contains various character types (with high probability).
        """

        password = generate_password(100)

        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()-_=+[]{}" for c in password)

        assert has_lower
        assert has_upper
        assert has_digit
        assert has_special


class TestBcryptPassword:
    """
    Test suite for bcrypt_password function.
    """

    def test_bcrypt_password_success(self):
        """
        Test successful password hashing.
        """

        plaintext = "test_password_123"
        hashed = bcrypt_password(plaintext)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")

    def test_bcrypt_password_custom_rounds(self):
        """
        Test password hashing with custom rounds.
        """

        plaintext = "test_password_123"
        hashed = bcrypt_password(plaintext, rounds=12)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")

    def test_bcrypt_password_empty_string(self):
        """
        Test that empty password raises PasswordError.
        """

        with pytest.raises(PasswordError, match="Plaintext password cannot be empty"):
            bcrypt_password("")

    def test_bcrypt_password_none_input(self):
        """
        Test that None input raises PasswordError.
        """

        with pytest.raises(PasswordError, match="Plaintext password cannot be empty"):
            bcrypt_password(None)

    def test_bcrypt_password_verification(self):
        """
        Test that hashed password can be verified.
        """

        plaintext = "test_password_123"
        hashed = bcrypt_password(plaintext)

        assert bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))

    def test_bcrypt_password_different_passwords_different_hashes(self):
        """
        Test that different passwords produce different hashes.
        """

        password1 = "password1"
        password2 = "password2"

        hash1 = bcrypt_password(password1)
        hash2 = bcrypt_password(password2)

        assert hash1 != hash2

    def test_bcrypt_password_same_password_different_hashes(self):
        """
        Test that same password produces different hashes (due to salt).
        """

        password = "same_password"

        hash1 = bcrypt_password(password)
        hash2 = bcrypt_password(password)

        assert hash1 != hash2

    def test_bcrypt_password_unicode_support(self):
        """
        Test that bcrypt handles unicode passwords correctly.
        """

        unicode_password = "árvíztűrőtükörfúrógép_123_🚀"
        hashed = bcrypt_password(unicode_password)

        assert bcrypt.checkpw(unicode_password.encode("utf-8"), hashed.encode("utf-8"))

    @mock.patch("launchpad.password.bcrypt.hashpw")
    def test_bcrypt_password_bcrypt_error(self, mock_hashpw):
        """
        Test that bcrypt errors are properly handled.
        """

        mock_hashpw.side_effect = Exception("Bcrypt error")

        with pytest.raises(
            PasswordError, match="Failed to bcrypt password: Bcrypt error"
        ):
            bcrypt_password("test_password")

    @mock.patch("launchpad.password.bcrypt.gensalt")
    def test_bcrypt_password_gensalt_error(self, mock_gensalt):
        """
        Test that gensalt errors are properly handled.
        """

        mock_gensalt.side_effect = Exception("Gensalt error")

        with pytest.raises(
            PasswordError, match="Failed to bcrypt password: Gensalt error"
        ):
            bcrypt_password("test_password")


class TestGetPasswordMtime:
    """
    Test suite for get_password_mtime function.
    """

    def test_get_password_mtime_format(self):
        """
        Test that mtime returns RFC3339 format.
        """

        mtime = get_password_mtime()

        assert isinstance(mtime, str)
        assert len(mtime) == 20
        assert mtime.endswith("Z")
        assert "T" in mtime

    def test_get_password_mtime_parsable(self):
        """
        Test that mtime can be parsed as RFC3339.
        """

        mtime = get_password_mtime()

        parsed = datetime.fromisoformat(mtime.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)
        assert parsed.tzinfo == timezone.utc

    def test_get_password_mtime_recent(self):
        """
        Test that mtime is recent (within last minute).
        """

        mtime = get_password_mtime()
        parsed = datetime.fromisoformat(mtime.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        time_diff = abs((now - parsed).total_seconds())
        assert time_diff < 60

    def test_get_password_mtime_utc(self):
        """
        Test that mtime is in UTC timezone.
        """

        mtime = get_password_mtime()
        parsed = datetime.fromisoformat(mtime.replace("Z", "+00:00"))

        assert parsed.tzinfo == timezone.utc

    @mock.patch("launchpad.password.datetime")
    def test_get_password_mtime_mocked_time(self, mock_datetime):
        """
        Test mtime with mocked datetime.
        """

        fixed_time = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time

        mtime = get_password_mtime()

        assert mtime == "2024-01-15T12:30:45Z"


class TestResolvePlaintextPassword:
    """
    Test suite for resolve_plaintext_password function.
    """

    def test_resolve_plaintext_password_with_provided(self):
        """
        Test that provided password is returned as-is.
        """

        provided = "my_custom_password"
        result = resolve_plaintext_password(provided)

        assert result == provided

    def test_resolve_plaintext_password_empty_string(self):
        """
        Test that empty string triggers password generation.
        """

        result = resolve_plaintext_password("")

        assert isinstance(result, str)
        assert len(result) == 24
        assert result != ""

    def test_resolve_plaintext_password_none_input(self):
        """
        Test that None input triggers password generation.
        """

        result = resolve_plaintext_password(None)

        assert isinstance(result, str)
        assert len(result) == 24
        assert result != ""

    def test_resolve_plaintext_password_no_input(self):
        """
        Test that no input triggers password generation.
        """

        result = resolve_plaintext_password()

        assert isinstance(result, str)
        assert len(result) == 24
        assert result != ""

    def test_resolve_plaintext_password_whitespace_only_returns_as_is(self):
        """
        Test that whitespace-only input is returned as-is (truthy check).
        """

        result = resolve_plaintext_password("   ")

        assert isinstance(result, str)
        assert result == "   "

    def test_resolve_plaintext_password_generated_is_secure(self):
        """
        Test that generated password is secure.
        """

        result = resolve_plaintext_password("")

        expected_chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}"
        assert all(c in expected_chars for c in result)

    def test_resolve_plaintext_password_different_calls_different_passwords(self):
        """
        Test that different calls generate different passwords.
        """

        result1 = resolve_plaintext_password("")
        result2 = resolve_plaintext_password("")

        assert result1 != result2

    @mock.patch("launchpad.password.generate_password")
    def test_resolve_plaintext_password_calls_generate_when_empty(self, mock_generate):
        """
        Test that empty input calls generate_password.
        """

        mock_generate.return_value = "generated_password"

        result = resolve_plaintext_password("")

        mock_generate.assert_called_once()
        assert result == "generated_password"

    @mock.patch("launchpad.password.generate_password")
    def test_resolve_plaintext_password_does_not_call_generate_when_provided(
        self, mock_generate
    ):
        """
        Test that provided password does not call generate_password.
        """

        result = resolve_plaintext_password("provided_password")

        mock_generate.assert_not_called()
        assert result == "provided_password"
