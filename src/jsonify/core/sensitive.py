"""Detect likely sensitive data in a JSON document by key name *and* value.

Detection is heuristic: it favours precision over recall (so a masked
export doesn't destroy ordinary data) and should never be treated as a
guarantee that a document contains no secrets.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass

from jsonify.core.masking import DEFAULT_SENSITIVE_FIELDS, MaskType, mask_value
from jsonify.core.models import JSONValue
from jsonify.core.pointer import PathSegment, to_json_path

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_JWT = re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$")
_PHONE_CHARS = re.compile(r"^\+?[\d\s().-]{9,22}$")
_CONNECTION_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^\s:/@]+:[^\s@]+@\S+")
_CONNECTION_KEYVALUE = re.compile(r"(?i)\b(password|pwd)\s*=\s*[^;\s]+")
_API_KEY_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{20,}=*"),
)

_PHONE_KEY_HINTS = ("phone", "mobile", "tel", "fax")
_PASSWORD_KEYS = {"password", "passwd", "pwd"}

CATEGORIES = (
    "email",
    "phone",
    "jwt",
    "api_key",
    "connection_string",
    "password",
    "token",
    "secret",
)


@dataclass(frozen=True, slots=True)
class SensitiveFinding:
    """One value that looks sensitive."""

    segments: tuple[PathSegment, ...]
    category: str
    reason: str  # "key name" or "value pattern"
    mask_type: MaskType

    @property
    def path(self) -> str:
        return to_json_path(list(self.segments))


def detect_sensitive_data(payload: JSONValue) -> list[SensitiveFinding]:
    """Find likely sensitive scalar values anywhere in ``payload``."""

    findings: list[SensitiveFinding] = []
    _walk(payload, (), None, findings)
    return findings


def safe_mask(payload: JSONValue) -> tuple[JSONValue, list[SensitiveFinding]]:
    """Return a copy of ``payload`` with every detected value masked."""

    findings = detect_sensitive_data(payload)
    return mask_paths(payload, findings), findings


def mask_paths(payload: JSONValue, findings: list[SensitiveFinding]) -> JSONValue:
    """Mask the values at the given findings' paths (never mutates ``payload``)."""

    result = deepcopy(payload)

    for finding in findings:
        if not finding.segments:
            result = mask_value(result, finding.mask_type)
            continue

        parent = result
        for segment in finding.segments[:-1]:
            parent = parent[segment]  # type: ignore[index]

        last = finding.segments[-1]
        parent[last] = mask_value(parent[last], finding.mask_type)  # type: ignore[index]

    return result


def _walk(
    node: JSONValue,
    segments: tuple[PathSegment, ...],
    key: str | None,
    findings: list[SensitiveFinding],
) -> None:
    if isinstance(node, dict):
        for child_key, child in node.items():
            _walk(child, (*segments, child_key), child_key, findings)
        return

    if isinstance(node, list):
        for index, child in enumerate(node):
            _walk(child, (*segments, index), None, findings)
        return

    finding = _classify(node, key)
    if finding is not None:
        category, reason, mask_type = finding
        findings.append(SensitiveFinding(segments, category, reason, mask_type))


def _classify(value: JSONValue, key: str | None) -> tuple[str, str, MaskType] | None:
    if value is None or isinstance(value, bool) or value == "":
        return None

    lowered_key = (key or "").casefold()

    if isinstance(value, str):
        text = value.strip()

        if _JWT.match(text):
            return "jwt", "value pattern", MaskType.FULL

        if _CONNECTION_URL.match(text) or (
            ";" in text and _CONNECTION_KEYVALUE.search(text) and "=" in text
        ):
            return "connection_string", "value pattern", MaskType.FULL

        if any(pattern.search(text) for pattern in _API_KEY_PATTERNS):
            return "api_key", "value pattern", MaskType.FULL

        if _EMAIL.fullmatch(text):
            return "email", "value pattern", MaskType.EMAIL

        if _looks_like_phone(text, lowered_key):
            return "phone", "value pattern", MaskType.PARTIAL

    if lowered_key in DEFAULT_SENSITIVE_FIELDS:
        if lowered_key in _PASSWORD_KEYS:
            return "password", "key name", MaskType.FULL
        if "secret" in lowered_key:
            return "secret", "key name", MaskType.FULL
        return "token", "key name", MaskType.FULL

    return None


def _looks_like_phone(text: str, lowered_key: str) -> bool:
    if not _PHONE_CHARS.match(text):
        return False

    digits = re.sub(r"\D", "", text)
    if not 9 <= len(digits) <= 15:
        return False

    key_hint = any(hint in lowered_key for hint in _PHONE_KEY_HINTS)
    has_formatting = text.startswith("+") or any(ch in text for ch in " ()-.")

    # Plain digit runs (ids, timestamps) only count when the key says "phone".
    return key_hint or has_formatting and not _looks_like_date(text)


def _looks_like_date(text: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?", text))
