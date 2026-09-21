"""Tests for value-pattern sensitive-data detection and path masking."""

from __future__ import annotations

from jsonify.core.sensitive import detect_sensitive_data, mask_paths, safe_mask

_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


def _categories(payload) -> dict[str, str]:
    return {f.path: f.category for f in detect_sensitive_data(payload)}


def test_detects_email_by_value() -> None:
    assert _categories({"contact": "alice@example.com"}) == {"$.contact": "email"}


def test_detects_phone_with_formatting() -> None:
    result = _categories({"a": "+1 (555) 123-4567", "b": "555-123-4567"})

    assert result == {"$.a": "phone", "$.b": "phone"}


def test_plain_digit_string_is_not_phone_without_key_hint() -> None:
    assert _categories({"id": "1700000000"}) == {}
    assert _categories({"phone": "5551234567"}) == {"$.phone": "phone"}


def test_dates_are_not_phones() -> None:
    assert _categories({"date": "2024-01-15"}) == {}


def test_detects_jwt() -> None:
    assert _categories({"session": _JWT}) == {"$.session": "jwt"}


def test_detects_api_keys() -> None:
    payload = {
        "aws": "AKIAIOSFODNN7EXAMPLE",
        "openai": "sk-abcdefghijklmnopqrstuvwxyz123456",
        "gh": "ghp_" + "a" * 36,
    }

    assert set(_categories(payload).values()) == {"api_key"}
    assert len(_categories(payload)) == 3


def test_detects_connection_strings() -> None:
    payload = {
        "url": "postgres://user:hunter2@db.example.com:5432/app",
        "sql": "Server=db;Database=app;User Id=sa;Password=hunter2;",
    }

    assert set(_categories(payload).values()) == {"connection_string"}
    assert len(_categories(payload)) == 2


def test_detects_by_key_name() -> None:
    result = _categories({"password": "x", "token": "y", "client_secret": "z"})

    assert result == {"$.password": "password", "$.token": "token", "$.client_secret": "secret"}


def test_ignores_ordinary_values_and_empties() -> None:
    assert _categories({"name": "Alice", "n": 5, "ok": True, "password": ""}) == {}


def test_findings_inside_arrays_have_paths() -> None:
    assert _categories({"users": [{"email": "a@b.co"}]}) == {"$.users[0].email": "email"}


def test_mask_paths_does_not_mutate_and_masks_values() -> None:
    payload = {"user": {"email": "alice@example.com", "name": "Alice"}}

    masked, findings = safe_mask(payload)

    assert len(findings) == 1
    assert masked["user"]["email"] == "a****@example.com"
    assert masked["user"]["name"] == "Alice"
    assert payload["user"]["email"] == "alice@example.com"


def test_mask_paths_with_manual_findings() -> None:
    payload = {"k": ["aaaa", "bbbb"]}

    findings = [f for f in detect_sensitive_data({"k": ["x@y.co"]})]
    masked = mask_paths(payload, findings)

    assert masked["k"][0] != "aaaa"
    assert masked["k"][1] == "bbbb"
