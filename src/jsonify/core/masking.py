"""Core sensitive-data masking functionality."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum

from jsonify.core.models import JSONValue


class MaskType(StrEnum):
    """Supported masking strategies."""

    FULL = "full"
    EMAIL = "email"
    PARTIAL = "partial"


@dataclass(frozen=True, slots=True)
class MaskingRule:
    """Defines how a JSON field should be masked."""

    field_name: str
    mask_type: MaskType = MaskType.FULL


DEFAULT_SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "secret",
        "client_secret",
        "clientsecret",
        "api_key",
        "apikey",
        "access_token",
        "accesstoken",
        "refresh_token",
        "refreshtoken",
        "auth_token",
        "authtoken",
        "authorization",
        "bearer",
        "jwt",
        "token",
    }
)

_EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


def mask_json(
    payload: JSONValue,
    rules: list[MaskingRule],
) -> JSONValue:
    """
    Return a masked copy of a JSON payload.

    The original payload is never modified.
    """

    rule_map = {
        rule.field_name.casefold(): rule
        for rule in rules
    }

    copied_payload = deepcopy(payload)

    return _mask_value(
        copied_payload,
        rule_map,
    )


def detect_sensitive_fields(
    payload: JSONValue,
) -> list[str]:
    """
    Find field names that are likely to contain sensitive data.

    Detection is intentionally conservative and based only on known
    sensitive field names. It should not be treated as guaranteed
    sensitive-data detection.
    """

    found: set[str] = set()

    _collect_sensitive_fields(
        payload,
        found,
    )

    return sorted(
        found,
        key=str.casefold,
    )


def extract_field_names(
    payload: JSONValue,
) -> list[str]:
    """Return all unique object field names in a JSON payload."""

    fields: set[str] = set()

    _collect_field_names(
        payload,
        fields,
    )

    return sorted(
        fields,
        key=str.casefold,
    )


def mask_value(
    value: JSONValue,
    mask_type: MaskType,
) -> JSONValue:
    """Mask one JSON value."""

    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return "********"

    text = _primitive_to_text(value)

    if mask_type == MaskType.EMAIL:
        return _mask_email(text)

    if mask_type == MaskType.PARTIAL:
        return _mask_partial(text)

    return _mask_full(text)


def _mask_value(
    value: JSONValue,
    rules: dict[str, MaskingRule],
) -> JSONValue:
    """Recursively mask matching fields."""

    if isinstance(value, dict):
        result: dict[str, JSONValue] = {}

        for key, child in value.items():
            rule = rules.get(
                key.casefold()
            )

            if rule is not None:
                result[key] = mask_value(
                    child,
                    rule.mask_type,
                )
            else:
                result[key] = _mask_value(
                    child,
                    rules,
                )

        return result

    if isinstance(value, list):
        return [
            _mask_value(
                child,
                rules,
            )
            for child in value
        ]

    return value


def _collect_sensitive_fields(
    value: JSONValue,
    found: set[str],
) -> None:
    """Recursively find known sensitive field names."""

    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key.casefold()
                in DEFAULT_SENSITIVE_FIELDS
            ):
                found.add(key)

            _collect_sensitive_fields(
                child,
                found,
            )

    elif isinstance(value, list):
        for child in value:
            _collect_sensitive_fields(
                child,
                found,
            )


def _collect_field_names(
    value: JSONValue,
    fields: set[str],
) -> None:
    """Recursively collect JSON object field names."""

    if isinstance(value, dict):
        for key, child in value.items():
            fields.add(key)

            _collect_field_names(
                child,
                fields,
            )

    elif isinstance(value, list):
        for child in value:
            _collect_field_names(
                child,
                fields,
            )


def _mask_full(
    value: str,
) -> str:
    """Fully mask a string."""

    if not value:
        return ""

    return "*" * max(
        len(value),
        8,
    )


def _mask_partial(
    value: str,
) -> str:
    """
    Partially mask a value while retaining limited context.

    Examples:

        1234567890 -> 12******90
        ABCD       -> A**D
    """

    length = len(value)

    if length == 0:
        return ""

    if length == 1:
        return "*"

    if length <= 4:
        return (
            value[0]
            + ("*" * (length - 2))
            + value[-1]
        )

    visible = min(
        2,
        max(1, length // 4),
    )

    hidden_length = (
        length - (visible * 2)
    )

    return (
        value[:visible]
        + ("*" * hidden_length)
        + value[-visible:]
    )


def _mask_email(
    value: str,
) -> str:
    """
    Mask the local portion of an email address.

    Example:

        john.doe@example.com
        ->
        j*******@example.com
    """

    if not _EMAIL_PATTERN.match(value):
        return _mask_full(value)

    local_part, domain = value.split(
        "@",
        1,
    )

    if len(local_part) == 1:
        masked_local = "*"
    else:
        masked_local = (
            local_part[0]
            + ("*" * (len(local_part) - 1))
        )

    return (
        f"{masked_local}@{domain}"
    )


def _primitive_to_text(
    value: JSONValue,
) -> str:
    """Convert a primitive JSON value to text."""

    if isinstance(value, bool):
        return (
            "true"
            if value
            else "false"
        )

    return str(value)