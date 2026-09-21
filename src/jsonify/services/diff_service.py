"""Application service for comparing JSON documents."""

from __future__ import annotations

from jsonify.core.diff import JsonDiff, compare_json
from jsonify.core.models import JSONValue
from jsonify.core.parser import parse_json


class DiffService:
    """Provides JSON comparison operations for the UI layer."""

    def compare(
        self,
        old: JSONValue,
        new: JSONValue,
        *,
        array_identity_key: str | None = None,
    ) -> list[JsonDiff]:
        """Compare two already parsed JSON values."""

        return compare_json(
            old=old,
            new=new,
            array_identity_key=array_identity_key,
        )

    def compare_text(
        self,
        old_text: str,
        new_text: str,
        *,
        array_identity_key: str | None = None,
    ) -> list[JsonDiff]:
        """Parse and compare two JSON documents."""

        old_payload = parse_json(old_text)
        new_payload = parse_json(new_text)

        return compare_json(
            old=old_payload,
            new=new_payload,
            array_identity_key=array_identity_key,
        )
