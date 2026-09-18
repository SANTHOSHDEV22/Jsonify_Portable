"""Persistence operations for customers, orders, payments and licenses."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Customer,
    EmailDelivery,
    License,
    Order,
    Payment,
    WebhookEvent,
)


class LicenseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_customer(self, name: str, email: str) -> Customer:
        customer = self.db.scalar(select(Customer).where(Customer.email == email))
        if customer:
            customer.name = name
            return customer

        customer = Customer(name=name, email=email)
        self.db.add(customer)
        self.db.flush()
        return customer

    def create_order(
        self,
        *,
        order_id: str,
        customer: Customer,
        product: str,
        amount_paise: int,
        currency: str,
    ) -> Order:
        order = Order(
            order_id=order_id,
            customer_id=customer.id,
            product=product,
            amount_paise=amount_paise,
            currency=currency,
            status="pending",
        )
        self.db.add(order)
        self.db.flush()
        return order

    def update_payment_link(
        self, order: Order, payment_link_id: str, checkout_url: str
    ) -> None:
        order.payment_link_id = payment_link_id
        order.checkout_url = checkout_url

    def get_order(self, order_id: str) -> Order | None:
        return self.db.scalar(select(Order).where(Order.order_id == order_id))

    def get_payment(self, payment_id: str) -> Payment | None:
        return self.db.scalar(
            select(Payment).where(Payment.payment_id == payment_id)
        )

    def create_payment(
        self,
        *,
        order: Order,
        payment_id: str,
        amount_paise: int,
        currency: str,
        status: str,
    ) -> Payment:
        payment = Payment(
            payment_id=payment_id,
            order_id=order.id,
            amount_paise=amount_paise,
            currency=currency,
            status=status,
            provider="razorpay",
        )
        self.db.add(payment)
        order.status = "paid"
        order.paid_at = datetime.now(timezone.utc)
        self.db.flush()
        return payment

    def get_license_for_order(self, order: Order) -> License | None:
        return self.db.scalar(
            select(License).where(License.order_id == order.id)
        )

    def create_license(
        self,
        *,
        order: Order,
        license_id: str,
        licensed_to: str,
        email: str,
        license_code: str,
    ) -> License:
        license_record = License(
            license_id=license_id,
            order_id=order.id,
            licensed_to=licensed_to,
            email=email,
            tier="pro",
            license_code=license_code,
            expires_at=None,
            active=True,
        )
        self.db.add(license_record)
        self.db.flush()
        return license_record

    def get_webhook_event(
        self, provider: str, event_id: str
    ) -> WebhookEvent | None:
        return self.db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.provider == provider,
                WebhookEvent.event_id == event_id,
            )
        )

    def create_webhook_event(
        self,
        *,
        provider: str,
        event_id: str,
        event_type: str,
        payload: str,
    ) -> WebhookEvent:
        event = WebhookEvent(
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            processed=False,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def mark_webhook_processed(self, event: WebhookEvent) -> None:
        event.processed = True
        event.processed_at = datetime.now(timezone.utc)

    def create_email_delivery(
        self, license_record: License, recipient: str
    ) -> EmailDelivery:
        delivery = EmailDelivery(
            license_id=license_record.id,
            recipient=recipient,
            status="pending",
        )
        self.db.add(delivery)
        self.db.flush()
        return delivery

    def mark_email_sent(self, delivery: EmailDelivery) -> None:
        delivery.status = "sent"
        delivery.attempts += 1
        delivery.sent_at = datetime.now(timezone.utc)
        delivery.last_error = None

    def mark_email_failed(self, delivery: EmailDelivery, error: str) -> None:
        delivery.status = "failed"
        delivery.attempts += 1
        delivery.last_error = error[:4000]
