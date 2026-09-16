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
    ) -> list[JsonDiff]:
        """Compare two already parsed JSON values."""

        return compare_json(
            old=old,
            new=new,
        )

    def compare_text(
        self,
        old_text: str,
        new_text: str,
    ) -> list[JsonDiff]:
        """Parse and compare two JSON documents."""

        old_payload = parse_json(old_text)
        new_payload = parse_json(new_text)

        return compare_json(
            old=old_payload,
            new=new_payload,
        )