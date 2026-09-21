"""Tests for the developer utilities."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from jsonify.core.devtools import (
    DevToolError,
    base64_decode,
    base64_encode,
    compute_hashes,
    convert_timestamp,
    decode_jwt,
    describe_uuid,
    find_timestamps,
    find_uuids,
    generate_uuids,
    json_escape,
    json_unescape,
)

_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4iLCJpYXQiOjE1MTYyMzkwMjIsImV4cCI6MTUxNjI0MjYyMn0."
    "signature"
)


def test_decode_jwt_header_payload_and_claims() -> None:
    info = decode_jwt(_JWT, now=datetime(2018, 1, 1, tzinfo=UTC))

    assert info.header["alg"] == "HS256"
    assert info.payload["name"] == "John"
    assert info.claims["Issued at"].startswith("2018-01-18")
    assert info.expired is False


def test_decode_jwt_reports_expired() -> None:
    assert decode_jwt(_JWT, now=datetime(2030, 1, 1, tzinfo=UTC)).expired is True


def test_decode_jwt_accepts_bearer_prefix() -> None:
    assert decode_jwt("Bearer " + _JWT).payload["sub"] == "1234567890"


def test_decode_jwt_rejects_garbage() -> None:
    with pytest.raises(DevToolError):
        decode_jwt("not.a-jwt")
    with pytest.raises(DevToolError):
        decode_jwt("a.b.c")


def test_base64_round_trip() -> None:
    encoded = base64_encode("héllo wörld")

    assert base64_decode(encoded) == "héllo wörld"


def test_base64_url_safe() -> None:
    encoded = base64_encode("???>>>", url_safe=True)

    assert "+" not in encoded and "/" not in encoded
    assert base64_decode(encoded, url_safe=True) == "???>>>"


def test_base64_decode_invalid() -> None:
    with pytest.raises(DevToolError):
        base64_decode("***not base64***")


def test_json_escape_round_trip() -> None:
    original = 'line1\nline2 "quoted" \\ tab\t'

    escaped = json_escape(original)

    assert "\n" not in escaped
    assert json_unescape(escaped) == original
    assert json_unescape(f'"{escaped}"') == original


def test_json_unescape_invalid() -> None:
    with pytest.raises(DevToolError):
        json_unescape("bad \\q escape")


def test_convert_timestamp_seconds_ms_iso() -> None:
    seconds = convert_timestamp("1700000000")
    millis = convert_timestamp("1700000000000")
    iso = convert_timestamp("2023-11-14T22:13:20Z")

    assert seconds.detected_as == "Unix seconds"
    assert millis.detected_as == "Unix milliseconds"
    assert iso.detected_as == "ISO-8601"
    assert seconds.unix_seconds == millis.unix_seconds == iso.unix_seconds == 1700000000
    assert seconds.iso_utc == "2023-11-14T22:13:20Z"


def test_convert_timestamp_invalid() -> None:
    with pytest.raises(DevToolError):
        convert_timestamp("yesterday")


def test_find_timestamps_in_payload() -> None:
    payload = {"created": 1700000000, "count": 3, "nested": [{"ts": 1700000000000}]}

    assert find_timestamps(payload) == ["$.created", "$.nested[0].ts"]


def test_generate_and_find_uuids() -> None:
    generated = generate_uuids(3)

    assert len(generated) == 3
    assert find_uuids(f"a {generated[0]} b {generated[0].upper()}") == [generated[0]]


def test_describe_uuid() -> None:
    assert "version 4" in describe_uuid(generate_uuids(1)[0])
    with pytest.raises(DevToolError):
        describe_uuid("nope")


def test_compute_hashes_known_values() -> None:
    hashes = compute_hashes("abc")

    assert hashes["md5"] == "900150983cd24fb0d6963f7d28e17f72"
    assert hashes["sha1"] == "a9993e364706816aba3e25717850c26c9cd0d89d"
    assert hashes["sha256"].startswith("ba7816bf8f01cfea")
