"""License management service for Jsonify."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import (
    InvalidSignature,
)
from cryptography.hazmat.primitives import (
    hashes,
    serialization,
)
from cryptography.hazmat.primitives.asymmetric import (
    padding,
    rsa,
)

from jsonify.core.licensing import (
    FREE_FEATURES,
    Feature,
    LicenseInfo,
    LicenseTier,
)


class LicenseError(ValueError):
    """Raised when a license cannot be validated."""


class LicenseService:
    """Provides Jsonify licensing and feature access."""

    PRODUCT_NAME = "jsonify"
    LICENSE_VERSION = 1

    def __init__(
        self,
        public_key_pem: bytes,
    ) -> None:
        public_key = (
            serialization.load_pem_public_key(
                public_key_pem
            )
        )

        if not isinstance(
            public_key,
            rsa.RSAPublicKey,
        ):
            raise LicenseError(
                "Jsonify requires an RSA public key."
            )

        self._public_key = public_key

        self._license = LicenseInfo(
            tier=LicenseTier.FREE
        )

    @property
    def current_license(
        self,
    ) -> LicenseInfo:
        """Return the active license."""

        return self._license

    def reset_to_free(self) -> None:
        """Reset Jsonify to Free mode."""

        self._license = LicenseInfo(
            tier=LicenseTier.FREE
        )

    def has_feature(
        self,
        feature: Feature,
    ) -> bool:
        """Return whether the active license allows a feature."""

        if feature in FREE_FEATURES:
            return True

        return self._license.is_pro

    def activate_file(
        self,
        file_path: str | Path,
    ) -> LicenseInfo:
        """Validate and activate a signed license file."""

        path = Path(file_path)

        try:
            document = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except OSError as error:
            raise LicenseError(
                f"Unable to open license: {error}"
            ) from error

        except json.JSONDecodeError as error:
            raise LicenseError(
                "The selected license file is invalid."
            ) from error

        license_info = (
            self._validate_document(
                document
            )
        )

        self._license = license_info

        return license_info

    def _validate_document(
        self,
        document: object,
    ) -> LicenseInfo:
        """Validate a signed license document."""

        if not isinstance(document, dict):
            raise LicenseError(
                "Invalid Jsonify license format."
            )

        payload = document.get(
            "payload"
        )

        signature_text = document.get(
            "signature"
        )

        if not isinstance(payload, dict):
            raise LicenseError(
                "License payload is missing."
            )

        if not isinstance(
            signature_text,
            str,
        ):
            raise LicenseError(
                "License signature is missing."
            )

        self._validate_payload(
            payload
        )

        signed_bytes = (
            self._canonical_payload(
                payload
            )
        )

        try:
            signature = base64.b64decode(
                signature_text,
                validate=True,
            )
        except ValueError as error:
            raise LicenseError(
                "License signature is invalid."
            ) from error

        try:
            self._public_key.verify(
                signature,
                signed_bytes,
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

        except InvalidSignature as error:
            raise LicenseError(
                (
                    "License verification failed. "
                    "The license may have been modified."
                )
            ) from error

        tier_text = payload.get(
            "tier"
        )

        try:
            tier = LicenseTier(
                tier_text
            )
        except ValueError as error:
            raise LicenseError(
                "Unknown license tier."
            ) from error

        expires_at = payload.get(
            "expires_at"
        )

        if (
            expires_at is not None
            and not isinstance(
                expires_at,
                str,
            )
        ):
            raise LicenseError(
                "Invalid license expiry date."
            )

        if (
            expires_at
            and self._is_expired(
                expires_at
            )
        ):
            raise LicenseError(
                "This Jsonify license has expired."
            )

        return LicenseInfo(
            tier=tier,
            licensed_to=str(
                payload.get(
                    "licensed_to",
                    "",
                )
            ),
            license_id=str(
                payload.get(
                    "license_id",
                    "",
                )
            ),
            expires_at=expires_at,
        )

    def _validate_payload(
        self,
        payload: dict[str, Any],
    ) -> None:
        """Validate required license metadata."""

        if (
            payload.get("product")
            != self.PRODUCT_NAME
        ):
            raise LicenseError(
                "This license is not for Jsonify."
            )

        if (
            payload.get(
                "license_version"
            )
            != self.LICENSE_VERSION
        ):
            raise LicenseError(
                "Unsupported license version."
            )

        if not isinstance(
            payload.get("license_id"),
            str,
        ):
            raise LicenseError(
                "License ID is missing."
            )

        if not isinstance(
            payload.get("licensed_to"),
            str,
        ):
            raise LicenseError(
                "Licensed user is missing."
            )

        tier = payload.get("tier")

        if tier not in {
            LicenseTier.FREE.value,
            LicenseTier.PRO.value,
        }:
            raise LicenseError(
                "Unknown license tier."
            )

    @staticmethod
    def _canonical_payload(
        payload: dict[str, Any],
    ) -> bytes:
        """Create deterministic bytes for signature verification."""

        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    @staticmethod
    def _is_expired(
        expires_at: str,
    ) -> bool:
        """Return whether a license has expired."""

        try:
            normalized = (
                expires_at.replace(
                    "Z",
                    "+00:00",
                )
            )

            expiry = datetime.fromisoformat(
                normalized
            )

        except ValueError as error:
            raise LicenseError(
                "Invalid license expiry date."
            ) from error

        if expiry.tzinfo is None:
            raise LicenseError(
                (
                    "License expiry date "
                    "must contain a timezone."
                )
            )

        return (
            datetime.now(timezone.utc)
            >= expiry.astimezone(
                timezone.utc
            )
        )