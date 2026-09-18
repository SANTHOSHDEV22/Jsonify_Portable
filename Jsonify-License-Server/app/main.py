"""Production-oriented Jsonify Pro licensing server."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.repositories.license_repository import LicenseRepository

load_dotenv()

PRODUCT_NAME = "jsonify"
PRODUCT_CODE = "jsonify-pro"
LICENSE_VERSION = 1
PRICE_PAISE = 25_000
CURRENCY = "INR"
LICENSE_CODE_PREFIX = "JPRO1-"

app = FastAPI(title="Jsonify License Server", version="1.0.0")


class PurchaseRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    product: str


class PurchaseResponse(BaseModel):
    order_id: str
    checkout_url: str


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


@app.on_event("startup")
def create_database_tables() -> None:
    """Convenient initial deployment bootstrap.

    For long-lived production systems, replace this with Alembic migrations.
    """
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jsonify-license-server"}


@app.post("/v1/purchases", response_model=PurchaseResponse)
async def create_purchase(
    request: PurchaseRequest,
    db: Session = Depends(get_db),
) -> PurchaseResponse:
    if request.product != PRODUCT_CODE:
        raise HTTPException(status_code=400, detail="Unknown product.")

    repo = LicenseRepository(db)
    order_id = secrets.token_urlsafe(18)
    name = request.name.strip()
    email = str(request.email).lower()

    try:
        customer = repo.get_or_create_customer(name, email)
        order = repo.create_order(
            order_id=order_id,
            customer=customer,
            product=PRODUCT_CODE,
            amount_paise=PRICE_PAISE,
            currency=CURRENCY,
        )

        payment_payload = {
            "amount": PRICE_PAISE,
            "currency": CURRENCY,
            "description": "Jsonify Pro - Lifetime License",
            "customer": {"name": name, "email": email},
            "notify": {"email": True, "sms": False},
            "reminder_enable": True,
            "notes": {
                "jsonify_order_id": order_id,
                "product": PRODUCT_CODE,
            },
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.razorpay.com/v1/payment_links/",
                json=payment_payload,
                auth=(
                    require_env("RAZORPAY_KEY_ID"),
                    require_env("RAZORPAY_KEY_SECRET"),
                ),
            )
            response.raise_for_status()
            payment_link = response.json()

        payment_link_id = str(payment_link.get("id", ""))
        checkout_url = str(payment_link.get("short_url", ""))

        if not payment_link_id or not checkout_url:
            raise HTTPException(
                status_code=502,
                detail="Invalid response from payment provider.",
            )

        repo.update_payment_link(order, payment_link_id, checkout_url)
        db.commit()

        return PurchaseResponse(order_id=order_id, checkout_url=checkout_url)

    except HTTPException:
        db.rollback()
        raise
    except httpx.HTTPError as error:
        db.rollback()
        raise HTTPException(
            status_code=502, detail="Unable to create payment link."
        ) from error
    except Exception:
        db.rollback()
        raise


@app.post("/v1/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    expected = hmac.new(
        require_env("RAZORPAY_WEBHOOK_SECRET").encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON.") from error

    event_type = str(event.get("event", "unknown"))
    payload = event.get("payload", {})
    payment_link = payload.get("payment_link", {}).get("entity", {})
    payment = payload.get("payment", {}).get("entity", {})

    # Prefer provider event identifiers when supplied; fall back to stable
    # payment/link information rather than random data.
    event_id = str(
        event.get("id")
        or payment.get("id")
        or payment_link.get("id")
        or hashlib.sha256(raw_body).hexdigest()
    )

    repo = LicenseRepository(db)

    existing_event = repo.get_webhook_event("razorpay", event_id)
    if existing_event and existing_event.processed:
        return {"ok": True}

    try:
        webhook_event = existing_event or repo.create_webhook_event(
            provider="razorpay",
            event_id=event_id,
            event_type=event_type,
            payload=raw_body.decode("utf-8"),
        )

        if event_type != "payment_link.paid":
            repo.mark_webhook_processed(webhook_event)
            db.commit()
            return {"ok": True}

        notes = payment_link.get("notes") or {}
        local_order_id = notes.get("jsonify_order_id")
        payment_id = str(payment.get("id", ""))

        if not local_order_id or not payment_id:
            raise HTTPException(status_code=400, detail="Payment metadata missing.")

        order = repo.get_order(str(local_order_id))
        if order is None:
            raise HTTPException(status_code=404, detail="Unknown Jsonify order.")

        if int(payment.get("amount", 0)) != PRICE_PAISE:
            raise HTTPException(status_code=400, detail="Incorrect payment amount.")

        if str(payment.get("currency", CURRENCY)).upper() != CURRENCY:
            raise HTTPException(status_code=400, detail="Incorrect payment currency.")

        if payment.get("status") not in {"captured", "authorized"}:
            raise HTTPException(status_code=400, detail="Payment is not complete.")

        existing_payment = repo.get_payment(payment_id)
        if existing_payment is None:
            repo.create_payment(
                order=order,
                payment_id=payment_id,
                amount_paise=PRICE_PAISE,
                currency=CURRENCY,
                status=str(payment.get("status")),
            )

        license_record = repo.get_license_for_order(order)
        if license_record is None:
            document = create_signed_license(
                name=order.customer.name,
                email=order.customer.email,
            )
            license_code = encode_license_code(document)
            license_record = repo.create_license(
                order=order,
                license_id=document["payload"]["license_id"],
                licensed_to=order.customer.name,
                email=order.customer.email,
                license_code=license_code,
            )
        else:
            license_code = license_record.license_code

        delivery = repo.create_email_delivery(
            license_record, order.customer.email
        )

        # Commit durable payment/license state before the external email call.
        db.commit()

        try:
            send_license_email(
                recipient=order.customer.email,
                name=order.customer.name,
                license_code=license_code,
            )
            repo.mark_email_sent(delivery)
            repo.mark_webhook_processed(webhook_event)
            db.commit()
        except Exception as error:
            repo.mark_email_failed(delivery, str(error))
            db.commit()
            # Return failure so the provider can retry. The payment/license
            # uniqueness constraints prevent duplicate issuance.
            raise HTTPException(
                status_code=503,
                detail="Payment recorded but license email delivery failed.",
            ) from error

        return {"ok": True}

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        # Another concurrent/retried webhook may have inserted the same
        # unique payment/event. Treat it as idempotent after rollback.
        return {"ok": True}
    except Exception:
        db.rollback()
        raise


def create_signed_license(name: str, email: str) -> dict[str, Any]:
    payload = {
        "product": PRODUCT_NAME,
        "license_version": LICENSE_VERSION,
        "license_id": f"JPRO-{secrets.token_hex(6).upper()}",
        "licensed_to": name,
        "email": email,
        "tier": "pro",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
    }

    signature = load_private_key().sign(
        canonical_payload(payload),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

    return {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def load_private_key() -> rsa.RSAPrivateKey:
    key_path = Path(require_env("JSONIFY_LICENSE_PRIVATE_KEY_PATH"))
    if not key_path.exists():
        raise RuntimeError("License private key does not exist.")

    key = serialization.load_pem_private_key(
        key_path.read_bytes(),
        password=None,
    )
    if not isinstance(key, rsa.RSAPrivateKey):
        raise RuntimeError("Jsonify requires an RSA private key.")
    return key


def canonical_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def encode_license_code(document: dict[str, Any]) -> str:
    raw = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{LICENSE_CODE_PREFIX}{encoded}"


def send_license_email(recipient: str, name: str, license_code: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Your Jsonify Pro License"
    message["From"] = require_env("SMTP_FROM")
    message["To"] = recipient
    message.set_content(
        f"""Hi {name},

Thank you for purchasing Jsonify Pro.

Your Jsonify Pro license code is:

{license_code}

Activation:
1. Open Jsonify.
2. Open License.
3. Choose "I Have a License Code".
4. Paste the complete code.
5. Click "Activate Pro".

Plan: Jsonify Pro
Price: ₹250
License: Lifetime / No expiration

Keep this email for your records.
"""
    )

    with smtplib.SMTP(
        require_env("SMTP_HOST"),
        int(os.getenv("SMTP_PORT", "587")),
        timeout=30,
    ) as smtp:
        smtp.starttls()
        smtp.login(
            require_env("SMTP_USERNAME"),
            require_env("SMTP_PASSWORD"),
        )
        smtp.send_message(message)
