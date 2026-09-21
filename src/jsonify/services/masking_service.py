"""Sensitive-data masking service for Jsonify."""

from __future__ import annotations

from jsonify.core.masking import (
    MaskingRule,
    MaskType,
    detect_sensitive_fields,
    extract_field_names,
    mask_json,
)
from jsonify.core.models import JSONValue


class MaskingService:
    """Provides sensitive-data masking operations."""

    def get_fields(
        self,
        payload: JSONValue,
    ) -> list[str]:
        """Return all unique field names."""

        return extract_field_names(payload)

    def detect_fields(
        self,
        payload: JSONValue,
    ) -> list[str]:
        """Return likely sensitive field names."""

        return detect_sensitive_fields(payload)

    def mask(
        self,
        payload: JSONValue,
        fields: list[str],
        *,
        email_fields: set[str] | None = None,
        partial_fields: set[str] | None = None,
    ) -> JSONValue:
        """Mask selected fields."""

        email_fields = {field.casefold() for field in (email_fields or set())}

        partial_fields = {field.casefold() for field in (partial_fields or set())}

        rules: list[MaskingRule] = []

        for field in fields:
            normalized = field.casefold()

            if normalized in email_fields:
                mask_type = MaskType.EMAIL

            elif normalized in partial_fields:
                mask_type = MaskType.PARTIAL

            else:
                mask_type = MaskType.FULL

            rules.append(
                MaskingRule(
                    field_name=field,
                    mask_type=mask_type,
                )
            )

        return mask_json(
            payload,
            rules,
        )
