"""Tests for the sensitive-data masking service."""

from __future__ import annotations

from jsonify.services.masking_service import (
    MaskingService,
)


def test_get_fields() -> None:
    service = MaskingService()

    payload = {
        "name": "Alice",
        "profile": {
            "email": "alice@example.com",
        },
    }

    result = service.get_fields(
        payload
    )

    assert result == [
        "email",
        "name",
        "profile",
    ]


def test_detect_fields() -> None:
    service = MaskingService()

    payload = {
        "username": "alice",
        "password": "secret",
        "token": "abc123",
    }

    result = service.detect_fields(
        payload
    )

    assert result == [
        "password",
        "token",
    ]


def test_full_mask_selected_field() -> None:
    service = MaskingService()

    payload = {
        "name": "Alice",
        "password": "secret123",
    }

    result = service.mask(
        payload=payload,
        fields=["password"],
    )

    assert result["name"] == "Alice"
    assert result["password"] != "secret123"


def test_email_field() -> None:
    service = MaskingService()

    payload = {
        "email": "alice@example.com",
    }

    result = service.mask(
        payload=payload,
        fields=["email"],
        email_fields={"email"},
    )

    assert (
        result["email"]
        == "a****@example.com"
    )


def test_partial_field() -> None:
    service = MaskingService()

    payload = {
        "accountNumber": "1234567890",
    }

    result = service.mask(
        payload=payload,
        fields=["accountNumber"],
        partial_fields={
            "accountNumber"
        },
    )

    assert (
        result["accountNumber"]
        == "12******90"
    )


def test_unselected_fields_are_unchanged() -> None:
    service = MaskingService()

    payload = {
        "name": "Alice",
        "email": "alice@example.com",
        "password": "secret",
    }

    result = service.mask(
        payload=payload,
        fields=["password"],
    )

    assert result["name"] == "Alice"

    assert (
        result["email"]
        == "alice@example.com"
    )