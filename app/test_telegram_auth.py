"""Focused security checks for Telegram Mini App authentication."""

import hashlib
import hmac
import unittest
from urllib.parse import urlencode

from app.telegram_auth import TelegramAuthError, validate_webapp_init_data


def signed_init_data(token: str, *, auth_date: int = 1_000) -> str:
    fields = {
        "auth_date": str(auth_date),
        "query_id": "query-123",
        "user": '{"id":12345,"first_name":"Олена","username":"olena"}',
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


class TelegramWebAppAuthTests(unittest.TestCase):
    def test_accepts_fresh_signed_identity(self) -> None:
        identity = validate_webapp_init_data(signed_init_data("test-token"), "test-token", now=1_100)
        self.assertEqual(identity.telegram_id, 12345)
        self.assertEqual(identity.first_name, "Олена")

    def test_rejects_tampered_or_expired_payload(self) -> None:
        with self.assertRaises(TelegramAuthError):
            validate_webapp_init_data(signed_init_data("test-token").replace("12345", "99999"), "test-token", now=1_100)
        with self.assertRaises(TelegramAuthError):
            validate_webapp_init_data(signed_init_data("test-token"), "test-token", now=5_000)


if __name__ == "__main__":
    unittest.main()
