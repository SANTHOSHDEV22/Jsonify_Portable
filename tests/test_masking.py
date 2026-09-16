"""Tests for core sensitive-data masking."""

from __future__ import annotations

from jsonify.core.masking import (
    MaskingRule,
    MaskType,
    detect_sensitive_fields,
    extract_field_names,
    mask_json,
)


def test_full_mask() -> None:
    payload = {
        "username": "alice",
        "password": "secret123",
    }

    result = mask_json(
        payload,
        [
            MaskingRule(
                "password",
                MaskType.FULL,
            )
        ],
    )

    assert result["username"] == "alice"

    assert result["password"] == (
        "*" * len("secret123")
    )


def test_original_payload_is_not_modified() -> None:
    payload = {
        "password": "secret123",
    }

    result = mask_json(
        payload,
        [
            MaskingRule(
                "password",
                MaskType.FULL,
            )
        ],
    )

    assert payload["password"] == "secret123"

    assert result["password"] != "secret123"


def test_nested_field_masking() -> None:
    payload = {
        "user": {
            "name": "Alice",
            "password": "secret",
        }
    }

    result = mask_json(
        payload,
        [
            MaskingRule(
                "password"
            )
        ],
    )

    assert (
        result["user"]["name"]
        == "Alice"
    )

    assert (
        result["user"]["password"]
        != "secret"
    )


def test_repeated_fields_are_all_masked() -> None:
    payload = {
        "users": [
            {
                "name": "Alice",
                "token": "token-one",
            },
            {
                "name": "Bob",
                "token": "token-two",
            },
        ]
    }

    result = mask_json(
        payload,
        [
            MaskingRule(
                "token"
            )
        ],
    )

    assert (
        result["users"][0]["token"]
        != "token-one"
    )

    assert (
        result["users"][1]["token"]
        != "token-two"
    )


def test_case_insensitive_field_matching() -> None:
    payload = {
        "Password": "secret",
    }

    result = mask_json(
        payload,
        [
            MaskingRule(
                "password"
            )
        ],
    )

    assert result["Password"] != "secret"


def test_email_masking() -> None:
    payload = {
        "email": "john.doe@example.com",
    }

    result = mask_json(
        payload,
        [
            MaskingRule(
                "email",
                MaskType.EMAIL,
            )
        ],
    )

    assert (
        result["email"]
        == "j*******@example.com"
    )


def test_partial_mask() -> None:
    payload = {
        "customerId": "1234567890",
    }

    result = mask_json(
        payload,
        [
            MaskingRule(
                "customerId",
                MaskType.PARTIAL,
            )
        ],
    )

    assert (
        result["customerId"]
        == "12******90"
    )


def test_detect_sensitive_fields() -> None:
    payload = {
        "username": "Alice",
        "password": "secret",
        "profile": {
            "token": "abc",
        },
    }

    result = detect_sensitive_fields(
        payload
    )

    assert "password" in result
    assert "token" in result
    assert "username" not in result


def test_extract_field_names() -> None:
    payload = {
        "id": 1,
        "user": {
            "name": "Alice",
            "email": "alice@example.com",
        },
    }

    result = extract_field_names(
        payload
    )

    assert result == [
        "email",
        "id",
        "name",
        "user",
    ]


def test_null_value_remains_null() -> None:
    payload = {
        "token": None,
    }

    result = mask_json(
        payload,
        [
            MaskingRule(
                "token"
            )
        ],
    )

    assert result["token"] is None