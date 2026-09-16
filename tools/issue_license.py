"""Issue a signed Jsonify Pro license."""

from __future__ import annotations

import base64
import getpass
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import (
    hashes,
    serialization,
)
from cryptography.hazmat.primitives.asymmetric import (
    padding,
    rsa,
)


def canonical_payload(
    payload: dict[str, object],
) -> bytes:
    """Serialize license payload deterministically."""

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def main() -> None:
    licensed_to = input(
        "Licensed to: "
    ).strip()

    if not licensed_to:
        raise ValueError(
            "Licensed user is required."
        )

    password = getpass.getpass(
        "Private key password: "
    )

    private_key_data = Path(
        "license_private.pem"
    ).read_bytes()

    private_key = (
        serialization.load_pem_private_key(
            private_key_data,
            password=password.encode(
                "utf-8"
            ),
        )
    )

    if not isinstance(
        private_key,
        rsa.RSAPrivateKey,
    ):
        raise TypeError(
            "Expected RSA private key."
        )

    license_id = (
        "JPRO-"
        + secrets.token_hex(6).upper()
    )

    payload: dict[str, object] = {
        "product": "jsonify",
        "license_version": 1,
        "license_id": license_id,
        "licensed_to": licensed_to,
        "tier": "pro",
        "issued_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "expires_at": None,
    }

    signature = private_key.sign(
        canonical_payload(
            payload
        ),
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

    output_directory = Path(
        "licenses"
    )

    output_directory.mkdir(
        exist_ok=True
    )

    output = (
        output_directory
        / f"{license_id}.jsonify-license"
    )

    output.write_text(
        json.dumps(
            document,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        f"License created: {output}"
    )


if __name__ == "__main__":
    main()