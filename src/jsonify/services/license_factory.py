"""License service creation."""

from __future__ import annotations

from importlib.resources import files

from jsonify.services.license_service import (
    LicenseService,
)


def create_license_service() -> LicenseService:
    """Create the Jsonify license service."""

    key_resource = (
        files("jsonify.resources")
        .joinpath(
            "license_public.pem"
        )
    )

    public_key = (
        key_resource.read_bytes()
    )

    return LicenseService(
        public_key
    )