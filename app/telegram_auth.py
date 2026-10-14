"""Server-side verification for Telegram Mini App and Login Widget identities."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import parse_qsl


class TelegramAuthError(ValueError):
    """Raised when Mini App data is missing, altered, or too old."""


@dataclass(frozen=True)
class TelegramIdentity:
    telegram_id: int
    username: str | None
    first_name: str | None


def validate_webapp_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 3_600,
    now: int | None = None,
) -> TelegramIdentity:
    """Validate Telegram's HMAC signature and return a trusted user identity.

    The browser-supplied ``initDataUnsafe`` object is intentionally never used.
    Only the original query string is verified according to Telegram's Mini App
    validation algorithm before its user data reaches application logic.
    """
    if not init_data or not bot_token:
        raise TelegramAuthError("Missing Telegram authentication data.")

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", None)
    auth_date = fields.get("auth_date")
    raw_user = fields.get("user")
    if not received_hash or not auth_date or not raw_user:
        raise TelegramAuthError("Telegram authentication data is incomplete.")

    try:
        issued_at = int(auth_date)
    except ValueError as error:
        raise TelegramAuthError("Telegram authentication timestamp is invalid.") from error
    current_time = int(time.time()) if now is None else now
    if issued_at > current_time + 60 or current_time - issued_at > max_age_seconds:
        raise TelegramAuthError("Telegram authentication data has expired.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramAuthError("Telegram authentication signature is invalid.")

    try:
        user = json.loads(raw_user)
        telegram_id = int(user["id"])
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise TelegramAuthError("Telegram user data is invalid.") from error
    if telegram_id <= 0:
        raise TelegramAuthError("Telegram user ID is invalid.")

    return TelegramIdentity(
        telegram_id=telegram_id,
        username=user.get("username") or None,
        first_name=user.get("first_name") or None,
    )


def validate_login_widget_data(
    payload: Mapping[str, object],
    bot_token: str,
    max_age_seconds: int = 3_600,
    now: int | None = None,
) -> TelegramIdentity:
    """Verify the legacy Telegram Login Widget payload before using its ID.

    The Login Widget and Mini Apps deliberately use different HMAC derivations.
    This function implements the Widget variant documented by Telegram and never
    trusts an ID until its signature and timestamp have been checked.
    """
    if not bot_token:
        raise TelegramAuthError("Missing Telegram authentication data.")

    received_hash = payload.get("hash")
    auth_date = payload.get("auth_date")
    telegram_id = payload.get("id")
    first_name = payload.get("first_name")
    if not isinstance(received_hash, str) or not received_hash or auth_date is None or telegram_id is None:
        raise TelegramAuthError("Telegram Login Widget data is incomplete.")

    try:
        issued_at = int(auth_date)
        parsed_telegram_id = int(telegram_id)
    except (TypeError, ValueError) as error:
        raise TelegramAuthError("Telegram Login Widget data is invalid.") from error
    if parsed_telegram_id <= 0 or not isinstance(first_name, str) or not first_name.strip():
        raise TelegramAuthError("Telegram Login Widget user data is invalid.")

    current_time = int(time.time()) if now is None else now
    if issued_at > current_time + 60 or current_time - issued_at > max_age_seconds:
        raise TelegramAuthError("Telegram Login Widget data has expired.")

    fields = {
        key: str(value)
        for key, value in payload.items()
        if key != "hash" and value is not None
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramAuthError("Telegram Login Widget signature is invalid.")

    username = payload.get("username")
    return TelegramIdentity(
        telegram_id=parsed_telegram_id,
        username=username if isinstance(username, str) and username else None,
        first_name=first_name.strip(),
    )
