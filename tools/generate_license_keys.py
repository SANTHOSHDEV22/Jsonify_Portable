"""Generate Jsonify license signing keys."""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import (
    serialization,
)
from cryptography.hazmat.primitives.asymmetric import (
    rsa,
)


def main() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=3072,
    )

    private_pem = (
        private_key.private_bytes(
            encoding=(
                serialization.Encoding.PEM
            ),
            format=(
                serialization
                .PrivateFormat.PKCS8
            ),
            encryption_algorithm=(
                serialization
                .BestAvailableEncryption(
                    input(
                        "Private key password: "
                    ).encode("utf-8")
                )
            ),
        )
    )

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=(
                serialization.Encoding.PEM
            ),
            format=(
                serialization
                .PublicFormat
                .SubjectPublicKeyInfo
            ),
        )
    )

    Path(
        "license_private.pem"
    ).write_bytes(
        private_pem
    )

    public_path = Path(
        "src/jsonify/resources/"
        "license_public.pem"
    )

    public_path.write_bytes(
        public_pem
    )

    print(
        "License keys generated."
    )

    print(
        "PUBLIC:",
        public_path,
    )

    print(
        "PRIVATE: license_private.pem"
    )

    print(
        "Keep the private key secret."
    )


if __name__ == "__main__":
    main()