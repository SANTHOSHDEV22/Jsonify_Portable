"""Generate sample JSON payloads from a JSON Schema — the reverse of
``core.schema_inference``.

Deterministic and dependency-free (no Faker): a small set of built-in
name/word/email pools driven by the property name, plus schema
constraints (``enum``, ``minimum``/``maximum``, ``minLength``/``maxLength``,
array ``minItems``/``maxItems``). A fixed ``seed`` makes output repeatable,
which matters for test-fixture generation.
"""

from __future__ import annotations

import random
import string
from typing import Any

from jsonify.core.models import JSONValue

_FIRST_NAMES = ("Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Heidi")
_LAST_NAMES = ("Smith", "Johnson", "Lee", "Garcia", "Brown", "Davis", "Wilson", "Miller")
_WORDS = ("lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit")
_DOMAINS = ("example.com", "test.org", "sample.net")

def _email(rng: random.Random) -> str:
    user = rng.choice(_FIRST_NAMES).lower()
    return f"{user}.{rng.randint(1, 999)}@{rng.choice(_DOMAINS)}"


def _date(rng: random.Random) -> str:
    return f"20{rng.randint(20, 25)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


_NAME_HINTS = {
    "email": _email,
    "name": lambda rng: f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}",
    "firstname": lambda rng: rng.choice(_FIRST_NAMES),
    "first_name": lambda rng: rng.choice(_FIRST_NAMES),
    "lastname": lambda rng: rng.choice(_LAST_NAMES),
    "last_name": lambda rng: rng.choice(_LAST_NAMES),
    "username": lambda rng: f"{rng.choice(_FIRST_NAMES).lower()}{rng.randint(1, 999)}",
    "phone": lambda rng: f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
    "url": lambda rng: f"https://{rng.choice(_DOMAINS)}/{rng.choice(_WORDS)}",
    "id": lambda rng: rng.randint(1, 100000),
    "uuid": lambda rng: str(_fake_uuid(rng)),
    "date": _date,
    "color": lambda rng: rng.choice(("red", "green", "blue", "black", "white")),
    "country": lambda rng: rng.choice(("US", "IN", "GB", "DE", "JP")),
}


class SchemaGenerationError(ValueError):
    """Raised when a schema can't be turned into sample data."""


def generate_payload(
    schema: dict[str, Any],
    *,
    include_optional: bool = True,
    array_min: int = 1,
    array_max: int = 3,
    seed: int | None = None,
) -> JSONValue:
    """Generate one sample value matching ``schema``."""

    rng = random.Random(seed)
    return _generate(schema, "", rng, include_optional, array_min, array_max)


def generate_payloads(
    schema: dict[str, Any],
    count: int,
    *,
    include_optional: bool = True,
    array_min: int = 1,
    array_max: int = 3,
    seed: int | None = None,
) -> list[JSONValue]:
    """Generate ``count`` independent samples matching ``schema``."""

    rng = random.Random(seed)
    return [
        _generate(schema, "", rng, include_optional, array_min, array_max)
        for _ in range(max(0, count))
    ]


def _generate(
    schema: dict[str, Any],
    property_name: str,
    rng: random.Random,
    include_optional: bool,
    array_min: int,
    array_max: int,
) -> JSONValue:
    if "enum" in schema and schema["enum"]:
        return rng.choice(schema["enum"])

    schema_type = schema.get("type", "any")
    if isinstance(schema_type, list):
        schema_type = rng.choice(schema_type) if schema_type else "any"

    if schema_type == "object":
        return _generate_object(schema, rng, include_optional, array_min, array_max)
    if schema_type == "array":
        return _generate_array(schema, property_name, rng, include_optional, array_min, array_max)
    if schema_type == "string":
        return _generate_string(schema, property_name, rng)
    if schema_type == "integer":
        return _generate_number(schema, rng, integer=True)
    if schema_type == "number":
        return _generate_number(schema, rng, integer=False)
    if schema_type == "boolean":
        return rng.choice((True, False))
    if schema_type == "null":
        return None

    return None  # "any" / unrecognized type


def _generate_object(
    schema: dict[str, Any],
    rng: random.Random,
    include_optional: bool,
    array_min: int,
    array_max: int,
) -> dict[str, JSONValue]:
    properties: dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", []))

    result: dict[str, JSONValue] = {}
    for name, child_schema in properties.items():
        if name not in required and not include_optional:
            continue
        result[name] = _generate(child_schema, name, rng, include_optional, array_min, array_max)

    return result


def _generate_array(
    schema: dict[str, Any],
    property_name: str,
    rng: random.Random,
    include_optional: bool,
    array_min: int,
    array_max: int,
) -> list[JSONValue]:
    items_schema = schema.get("items", {})
    low = schema.get("minItems", array_min)
    high = max(low, schema.get("maxItems", array_max))
    count = rng.randint(low, high)

    return [
        _generate(items_schema, property_name, rng, include_optional, array_min, array_max)
        for _ in range(count)
    ]


def _generate_string(schema: dict[str, Any], property_name: str, rng: random.Random) -> str:
    hint = _NAME_HINTS.get(property_name.lower().strip("_"))
    if hint is not None:
        value = hint(rng)
        return value if isinstance(value, str) else str(value)

    fmt = schema.get("format")
    if fmt == "email":
        return _NAME_HINTS["email"](rng)
    if fmt in ("date", "date-time"):
        return _NAME_HINTS["date"](rng)
    if fmt == "uuid":
        return str(_fake_uuid(rng))

    min_length = schema.get("minLength", 3)
    max_length = max(min_length, schema.get("maxLength", 10))
    length = rng.randint(min_length, max_length)

    words = [rng.choice(_WORDS) for _ in range(max(1, length // 5))]
    fallback = "".join(rng.choice(string.ascii_lowercase) for _ in range(length))
    text = " ".join(words)[:max_length] or fallback
    return text.strip() or "sample"


def _generate_number(schema: dict[str, Any], rng: random.Random, *, integer: bool) -> int | float:
    minimum = schema.get("minimum", 0)
    maximum = schema.get("maximum", minimum + 100)

    if integer:
        return rng.randint(int(minimum), int(maximum))
    return round(rng.uniform(float(minimum), float(maximum)), 2)


def _fake_uuid(rng: random.Random) -> str:
    hex_digits = "0123456789abcdef"

    def group(length: int) -> str:
        return "".join(rng.choice(hex_digits) for _ in range(length))

    return f"{group(8)}-{group(4)}-4{group(3)}-{rng.choice('89ab')}{group(3)}-{group(12)}"
