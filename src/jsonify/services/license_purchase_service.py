"""Client for Jsonify Pro purchases.

The desktop application never signs licenses and never contains the private
license key. It only asks the Jsonify backend to create a checkout session.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


class PurchaseError(RuntimeError):
    """Raised when a Pro purchase cannot be started."""


@dataclass(frozen=True, slots=True)
class PurchaseSession:
    """Checkout session returned by the Jsonify backend."""

    checkout_url: str
    order_id: str = ""


class LicensePurchaseService:
    """Calls the production Jsonify licensing/payment backend."""

    def __init__(
        self,
        base_url: str = "https://license.yourdomain.com",
        timeout_seconds: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def create_checkout(self, name: str, email: str) -> PurchaseSession:
        """Create the fixed-price ₹250 Jsonify Pro checkout."""

        try:
            response = httpx.post(
                f"{self._base_url}/v1/purchases",
                json={
                    "name": name,
                    "email": email,
                    "product": "jsonify-pro",
                },
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise PurchaseError(
                "Unable to start the Jsonify Pro purchase. "
                "Check your internet connection and try again."
            ) from error

        checkout_url = data.get("checkout_url")
        if not isinstance(checkout_url, str) or not checkout_url.startswith(
            ("https://", "http://")
        ):
            raise PurchaseError(
                "The purchase server returned an invalid checkout URL."
            )

        return PurchaseSession(
            checkout_url=checkout_url,
            order_id=str(data.get("order_id", "")),
        )
