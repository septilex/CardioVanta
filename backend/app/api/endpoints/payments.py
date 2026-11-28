"""Optional Stripe TEST-mode support. No association with accounts or assessments."""
import uuid

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from typing import Literal

from backend.app.core.config import settings
from backend.app.db.orm import SupportPayment, PaymentEvent, session
from backend.app.services.shared import limit, anonymous_id
from backend.app.auth.security import check_origin

router = APIRouter()


def enabled():
    return bool(settings.PAYMENTS_ENABLED and settings.STRIPE_SECRET_KEY and
                settings.STRIPE_SECRET_KEY.get_secret_value().startswith("sk_test_") and
                settings.STRIPE_WEBHOOK_SECRET and settings.DATABASE_URL and settings.REDIS_URL)


def require_payments():
    if not enabled():
        raise HTTPException(503, "Test support payments are not configured.")


class Checkout(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Literal[500, 1000, 2500]
    request_key: uuid.UUID


@router.get("/support/status")
def status():
    return {"enabled": enabled(), "test_mode": True, "currency": "usd", "amounts": [500, 1000, 2500]}


def create_checkout(payment):
    client = stripe.StripeClient(settings.require_secret("STRIPE_SECRET_KEY"), max_network_retries=0,
                                http_client=stripe.RequestsClient(timeout=10))
    return client.v1.checkout.sessions.create({
        "mode": "payment", "client_reference_id": str(payment.id),
        "line_items": [{"price_data": {"currency": "usd", "unit_amount": payment.amount,
                                       "product_data": {"name": "CardioVanta educational project — test support"}}, "quantity": 1}],
        "success_url": settings.APP_ORIGIN.rstrip("/")+"/support?checkout=returned",
        "cancel_url": settings.APP_ORIGIN.rstrip("/")+"/support?checkout=cancelled",
    }, options={"idempotency_key": "cv-support-"+payment.request_key})


@router.post("/support/checkout")
def checkout(body: Checkout, request: Request, db: Session = Depends(session)):
    require_payments()
    check_origin(request)
    limit("checkout", anonymous_id(request), 5, 60)
    payment = db.scalar(select(SupportPayment).where(SupportPayment.request_key == str(body.request_key)))
    if payment is None:
        payment = SupportPayment(request_key=str(body.request_key), amount=body.amount)
        db.add(payment)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            payment = db.scalar(select(SupportPayment).where(SupportPayment.request_key == str(body.request_key)))
    if payment.amount != body.amount:
        raise HTTPException(409, "Checkout amount changed. Start a new checkout.")
    try:
        checkout = create_checkout(payment)
        if checkout.livemode or not checkout.url.startswith("https://checkout.stripe.com/"):
            raise ValueError()
        payment.checkout_id = checkout.id
        db.commit()
        return {"url": checkout.url, "test_mode": True}
    except Exception:
        db.rollback()
        raise HTTPException(503, "Test checkout is temporarily unavailable.") from None


def record_event(db: Session, event):
    if event.get("livemode") is not False:
        raise HTTPException(400, "Live payment events are not accepted.")
    kind = event["type"]
    if kind not in ("checkout.session.completed", "checkout.session.async_payment_succeeded", "checkout.session.expired", "checkout.session.async_payment_failed"):
        return {"received": True}
    if db.get(PaymentEvent, event["id"]):
        return {"received": True}
    obj = event["data"]["object"]
    payment = db.scalar(select(SupportPayment).where(SupportPayment.checkout_id == obj["id"]).with_for_update())
    if not payment:
        raise HTTPException(503, "Checkout record is not ready. Retry delivery.")
    if obj.get("client_reference_id") != str(payment.id) or obj.get("amount_total") != payment.amount or obj.get("currency") != "usd":
        raise HTTPException(400, "Payment metadata does not match.")
    paid = kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded") and obj.get("payment_status") == "paid"
    if paid:
        payment.status = "paid"
    elif kind in ("checkout.session.expired", "checkout.session.async_payment_failed") and payment.status != "paid":
        payment.status = "failed"
    db.add(PaymentEvent(event_id=event["id"], payment_id=payment.id, event_type=kind))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # Simultaneous delivery of the same verified event is harmless.
    return {"received": True}


@router.post("/support/webhook")
async def webhook(request: Request, db: Session = Depends(session)):
    require_payments()
    try:
        event = stripe.Webhook.construct_event(await request.body(), request.headers.get("stripe-signature", ""),
                                              settings.require_secret("STRIPE_WEBHOOK_SECRET"), tolerance=300)
    except Exception:
        raise HTTPException(400, "Invalid webhook signature.") from None
    return await run_in_threadpool(record_event, db, event)
