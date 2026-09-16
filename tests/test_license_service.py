"""Tests for Jsonify licensing."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import (
    hashes,
    serialization,
)
from cryptography.hazmat.primitives.asymmetric import (
    padding,
    rsa,
)

from jsonify.core.licensing import (
    Feature,
    LicenseTier,
)
from jsonify.services.license_service import (
    LicenseError,
    LicenseService,
)


def create_keys() -> tuple[
    rsa.RSAPrivateKey,
    bytes,
]:
    private_key = (
        rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
    )

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=(
                serialization.Encoding.PEM
            ),
            format=(
                serialization.PublicFormat
                .SubjectPublicKeyInfo
            ),
        )
    )

    return (
        private_key,
        public_pem,
    )


def write_license(
    path: Path,
    private_key: rsa.RSAPrivateKey,
    *,
    tier: str = "pro",
) -> None:
    payload = {
        "product": "jsonify",
        "license_version": 1,
        "license_id": "TEST-001",
        "licensed_to": "Test User",
        "tier": tier,
        "issued_at": (
            "2026-09-17T00:00:00+00:00"
        ),
        "expires_at": None,
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    signature = private_key.sign(
        canonical,
        padding.PSS(
            mgf=padding.MGF1(
                hashes.SHA256()
            ),
            salt_length=(
                padding.PSS.MAX_LENGTH
            ),
        ),
        hashes.SHA256(),
    )

    document = {
        "payload": payload,
        "signature": (
            base64.b64encode(
                signature
            ).decode("ascii")
        ),
    }

    path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )


def test_default_is_free() -> None:
    _, public_key = create_keys()

    service = LicenseService(
        public_key
    )

    assert (
        service.current_license.tier
        == LicenseTier.FREE
    )


def test_free_feature_available() -> None:
    _, public_key = create_keys()

    service = LicenseService(
        public_key
    )

    assert service.has_feature(
        Feature.JSON_VIEWER
    )


def test_pro_feature_locked_in_free() -> None:
    _, public_key = create_keys()

    service = LicenseService(
        public_key
    )

    assert not service.has_feature(
        Feature.JSON_DIFF
    )


def test_valid_pro_license(
    tmp_path: Path,
) -> None:
    private_key, public_key = (
        create_keys()
    )

    license_path = (
        tmp_path
        / "test.jsonify-license"
    )

    write_license(
        license_path,
        private_key,
    )

    service = LicenseService(
        public_key
    )

    info = service.activate_file(
        license_path
    )

    assert info.is_pro

    assert service.has_feature(
        Feature.JSON_DIFF
    )

    assert service.has_feature(
        Feature.JSONPATH
    )


def test_modified_license_rejected(
    tmp_path: Path,
) -> None:
    private_key, public_key = (
        create_keys()
    )

    license_path = (
        tmp_path
        / "test.jsonify-license"
    )

    write_license(
        license_path,
        private_key,
    )

    document = json.loads(
        license_path.read_text(
            encoding="utf-8"
        )
    )

    document["payload"][
        "licensed_to"
    ] = "Modified User"

    license_path.write_text(
        json.dumps(document),
        encoding="utf-8",
    )

    service = LicenseService(
        public_key
    )

    with pytest.raises(
        LicenseError,
        match="verification failed",
    ):
        service.activate_file(
            license_path
        )


def test_reset_to_free(
    tmp_path: Path,
) -> None:
    private_key, public_key = (
        create_keys()
    )

    license_path = (
        tmp_path
        / "test.jsonify-license"
    )

    write_license(
        license_path,
        private_key,
    )

    service = LicenseService(
        public_key
    )

    service.activate_file(
        license_path
    )

    assert (
        service.current_license.is_pro
    )

    service.reset_to_free()

    assert not (
        service.current_license.is_pro
    )