"""Small developer utilities: JWT, Base64, escaping, timestamps, UUIDs, hashes."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from jsonify.core.models import JSONValue


class DevToolError(ValueError):
    """Raised when an input can't be processed by a developer tool."""


# ---------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------


@dataclass(slots=True)
class JwtInfo:
    """A decoded (NOT verified) JSON Web Token."""

    header: dict[str, Any]
    payload: dict[str, Any]
    signature_present: bool
    claims: dict[str, str] = field(default_factory=dict)
    expired: bool | None = None


_TIME_CLAIMS = {"exp": "Expires", "iat": "Issued at", "nbf": "Not before"}


def decode_jwt(token: str, *, now: datetime | None = None) -> JwtInfo:
    """Decode a JWT locally. The signature is *not* verified and no secret is used."""

    parts = token.strip().removeprefix("Bearer ").strip().split(".")
    if len(parts) != 3:
        raise DevToolError("A JWT has three dot-separated parts (header.payload.signature).")

    header = _decode_jwt_part(parts[0], "header")
    payload = _decode_jwt_part(parts[1], "payload")

    current = now or datetime.now(UTC)
    claims: dict[str, str] = {}
    expired: bool | None = None

    for claim, label in _TIME_CLAIMS.items():
        value = payload.get(claim)
        if isinstance(value, int | float) and not isinstance(value, bool):
            moment = datetime.fromtimestamp(value, UTC)
            claims[label] = moment.isoformat()
            if claim == "exp":
                expired = moment < current

    return JwtInfo(header, payload, bool(parts[2]), claims, expired)


def _decode_jwt_part(part: str, name: str) -> dict[str, Any]:
    try:
        decoded = json.loads(_b64url_decode(part))
    except (ValueError, binascii.Error) as error:
        raise DevToolError(f"The JWT {name} is not valid Base64URL-encoded JSON.") from error

    if not isinstance(decoded, dict):
        raise DevToolError(f"The JWT {name} must be a JSON object.")

    return decoded


def _b64url_decode(text: str) -> bytes:
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded)


# ---------------------------------------------------------------------
# Base64
# ---------------------------------------------------------------------


def base64_encode(text: str, *, url_safe: bool = False) -> str:
    raw = text.encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw) if url_safe else base64.b64encode(raw)
    return encoded.decode("ascii")


def base64_decode(text: str, *, url_safe: bool = False) -> str:
    cleaned = re.sub(r"\s+", "", text)
    padded = cleaned + "=" * (-len(cleaned) % 4)

    try:
        raw = (
            base64.urlsafe_b64decode(padded)
            if url_safe
            else base64.b64decode(padded, validate=True)
        )
        return raw.decode("utf-8")
    except (binascii.Error, ValueError) as error:
        raise DevToolError(f"Invalid Base64 input: {error}") from error


# ---------------------------------------------------------------------
# JSON string escaping
# ---------------------------------------------------------------------


def json_escape(text: str) -> str:
    """Escape ``text`` so it can sit inside a JSON string literal."""

    return json.dumps(text, ensure_ascii=False)[1:-1]


def json_unescape(text: str) -> str:
    """Reverse :func:`json_escape` (accepts input with or without surrounding quotes)."""

    candidate = (
        text if text.startswith('"') and text.endswith('"') and len(text) >= 2 else f'"{text}"'
    )

    try:
        result = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise DevToolError(f"Not a valid escaped JSON string: {error.msg}") from error

    return str(result)


# ---------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------


@dataclass(slots=True)
class TimestampInfo:
    """One instant expressed in the common formats."""

    unix_seconds: int
    unix_milliseconds: int
    iso_utc: str
    detected_as: str


def convert_timestamp(text: str) -> TimestampInfo:
    """Detect a Unix seconds/milliseconds value or ISO-8601 date and convert it."""

    value = text.strip()
    if not value:
        raise DevToolError("Enter a Unix timestamp or an ISO-8601 date.")

    if re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        number = float(value)
        if abs(number) >= 1e11:
            moment = datetime.fromtimestamp(number / 1000, UTC)
            detected = "Unix milliseconds"
        else:
            moment = datetime.fromtimestamp(number, UTC)
            detected = "Unix seconds"
    else:
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise DevToolError("Not a Unix timestamp or ISO-8601 date.") from error
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        moment = moment.astimezone(UTC)
        detected = "ISO-8601"

    seconds = int(moment.timestamp())
    return TimestampInfo(
        unix_seconds=seconds,
        unix_milliseconds=int(moment.timestamp() * 1000),
        iso_utc=moment.isoformat().replace("+00:00", "Z"),
        detected_as=detected,
    )


def find_timestamps(payload: JSONValue, *, min_year: int = 2000, max_year: int = 2100) -> list[str]:
    """List paths of numeric values that plausibly are Unix timestamps."""

    lower = datetime(min_year, 1, 1, tzinfo=UTC).timestamp()
    upper = datetime(max_year, 1, 1, tzinfo=UTC).timestamp()
    found: list[str] = []

    def walk(node: JSONValue, path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, f"{path}.{key}")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")
        elif isinstance(node, int | float) and not isinstance(node, bool):
            if lower <= node <= upper or lower * 1000 <= node <= upper * 1000:
                found.append(path)

    walk(payload, "$")
    return found


# ---------------------------------------------------------------------
# UUID
# ---------------------------------------------------------------------

_UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def generate_uuids(count: int = 1, *, version: int = 4) -> list[str]:
    if version not in (1, 4):
        raise DevToolError("Only UUID versions 1 and 4 can be generated.")
    factory = uuid.uuid1 if version == 1 else uuid.uuid4
    return [str(factory()) for _ in range(max(1, min(count, 1000)))]


def find_uuids(text: str) -> list[str]:
    """Return every UUID-looking token in ``text`` (in order, deduplicated)."""

    seen: dict[str, None] = {}
    for match in _UUID_PATTERN.findall(text):
        seen.setdefault(match.lower(), None)
    return list(seen)


def describe_uuid(value: str) -> str:
    try:
        parsed = uuid.UUID(value.strip())
    except ValueError as error:
        raise DevToolError("Not a valid UUID.") from error
    return f"{parsed}  (version {parsed.version}, variant {parsed.variant})"


# ---------------------------------------------------------------------
# Hashes
# ---------------------------------------------------------------------

HASH_ALGORITHMS = ("md5", "sha1", "sha256", "sha512", "sha3_256", "blake2b")


def compute_hashes(text: str) -> dict[str, str]:
    """Hash ``text`` (UTF-8) with every common algorithm."""

    raw = text.encode("utf-8")
    return {name: hashlib.new(name, raw).hexdigest() for name in HASH_ALGORITHMS}
