"""Billing API (Stripe + LiqPay)

MVP goals:
- Create checkout (stripe redirect URL OR liqpay form payload)
- Receive webhooks and grant entitlement

NOTE: This is intentionally minimal and expects secrets in env/.env.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth import get_current_user
from server.config import get_settings
from database.models import BillingEvent, BillingMode, BillingOrder, BillingProvider, BillingStatus
from database.storage import DatabaseStorage, get_db

settings = get_settings()
router = APIRouter(prefix="/api/billing", tags=["Billing"])


def _require_billing_enabled():
    if not settings.billing_enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Billing is disabled")


def _get_amount_cents(mode: BillingMode) -> int:
    if mode == BillingMode.ONE_TIME:
        return int(settings.billing_one_time_amount_cents)
    return int(settings.billing_subscription_amount_cents)


def _grant_entitlement(storage: DatabaseStorage, user_db_id: int, mode: BillingMode, product_key: str):
    # ONE_TIME: lifetime access
    # SUBSCRIPTION: grant 31 days from now (webhook renewals extend it)
    active_until = None
    if mode == BillingMode.SUBSCRIPTION:
        active_until = datetime.utcnow() + timedelta(days=31)
    return storage.upsert_entitlement(user_id=user_db_id, product_key=product_key, active_until=active_until)


class ProductResponse(BaseModel):
    product_key: str
    name: str
    currency: str
    one_time_amount_cents: int
    subscription_amount_cents: int
    providers: list[str]


class CheckoutRequest(BaseModel):
    provider: Literal["stripe", "liqpay"]
    mode: Literal["one_time", "subscription"] = "one_time"
    product_key: str = Field(default_factory=lambda: settings.billing_product_key)


class CheckoutResponse(BaseModel):
    provider: str
    order_id: str

    # Stripe
    redirect_url: Optional[str] = None

    # LiqPay
    form_url: Optional[str] = None
    liqpay_data: Optional[str] = None
    liqpay_signature: Optional[str] = None


@router.get("/products", response_model=list[ProductResponse])
async def list_products():
    providers: list[str] = []
    if settings.stripe_secret_key:
        providers.append("stripe")
    if settings.liqpay_public_key and settings.liqpay_private_key:
        providers.append("liqpay")

    return [
        ProductResponse(
            product_key=settings.billing_product_key,
            name=settings.billing_product_name,
            currency=settings.billing_currency,
            one_time_amount_cents=int(settings.billing_one_time_amount_cents),
            subscription_amount_cents=int(settings.billing_subscription_amount_cents),
            providers=providers,
        )
    ]


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_billing_enabled()

    try:
        mode = BillingMode.ONE_TIME if body.mode == "one_time" else BillingMode.SUBSCRIPTION
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid mode")

    amount_cents = _get_amount_cents(mode)
    if amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount is not configured (set billing_*_amount_cents)",
        )

    provider = BillingProvider.STRIPE if body.provider == "stripe" else BillingProvider.LIQPAY

    storage = DatabaseStorage(db)
    order = BillingOrder(
        order_id=str(uuid.uuid4()),
        user_id=current_user.id,
        provider=provider,
        mode=mode,
        product_key=body.product_key,
        amount_cents=amount_cents,
        currency=settings.billing_currency,
    )
    storage.create_billing_order(order)

    base = settings.public_base_url.rstrip("/")

    if provider == BillingProvider.STRIPE:
        if not settings.stripe_secret_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe is not configured")

        import stripe  # lazy import

        stripe.api_key = settings.stripe_secret_key

        order_id_str = str(order.order_id)
        product_key_str = str(order.product_key)

        success_url = f"{base}/web/success.html?provider=stripe&order_id={order_id_str}"
        cancel_url = f"{base}/web/account.html?canceled=1"

        currency = settings.billing_currency.lower()

        if mode == BillingMode.ONE_TIME:
            session = stripe.checkout.Session.create(
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=current_user.email,
                client_reference_id=order_id_str,
                metadata={
                    "order_id": order_id_str,
                    "product_key": product_key_str,
                    "mode": str(mode.value),
                    "user_db_id": str(current_user.id),
                    "user_uuid": current_user.user_id,
                },
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {"name": settings.billing_product_name},
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
            )
        else:
            # Subscription via inline price_data (MVP)
            session = stripe.checkout.Session.create(
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=current_user.email,
                client_reference_id=order_id_str,
                metadata={
                    "order_id": order_id_str,
                    "product_key": product_key_str,
                    "mode": str(mode.value),
                    "user_db_id": str(current_user.id),
                    "user_uuid": current_user.user_id,
                },
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "product_data": {"name": settings.billing_product_name},
                            "unit_amount": amount_cents,
                            "recurring": {"interval": "month"},
                        },
                        "quantity": 1,
                    }
                ],
            )

        setattr(order, "provider_checkout_id", str(session.id))
        storage.db.commit()

        return CheckoutResponse(provider="stripe", order_id=str(order.order_id), redirect_url=session.url)

    # LiqPay
    if not (settings.liqpay_public_key and settings.liqpay_private_key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LiqPay is not configured")

    if mode == BillingMode.SUBSCRIPTION:
        # LiqPay recurring payments require separate configuration (recurring API)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LiqPay subscriptions are not enabled in this MVP (use Stripe subscription or LiqPay one_time)",
        )

    server_url = f"{base}/api/billing/webhooks/liqpay"
    result_url = f"{base}/web/success.html?provider=liqpay&order_id={order.order_id}"

    payload = {
        "public_key": settings.liqpay_public_key,
        "version": "3",
        "action": "pay",
        "amount": round(amount_cents / 100.0, 2),
        "currency": settings.billing_currency,
        "description": settings.billing_product_name,
        "order_id": order.order_id,
        "server_url": server_url,
        "result_url": result_url,
    }

    data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    signature_src = settings.liqpay_private_key + data + settings.liqpay_private_key
    signature = base64.b64encode(hashlib.sha1(signature_src.encode("utf-8")).digest()).decode("ascii")

    order.provider_checkout_id = order.order_id
    storage.db.commit()

    return CheckoutResponse(
        provider="liqpay",
        order_id=str(order.order_id),
        form_url="https://www.liqpay.ua/api/3/checkout",
        liqpay_data=data,
        liqpay_signature=signature,
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    if not sig_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature")

    import stripe

    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=settings.stripe_webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook: {e}")

    storage = DatabaseStorage(db)
    storage.record_billing_event(
        BillingEvent(provider=BillingProvider.STRIPE, event_id=getattr(event, "id", None), payload=payload.decode("utf-8", errors="replace"))
    )

    event_type = getattr(event, "type", "")

    # Minimal handling: checkout.session.completed grants access
    if event_type == "checkout.session.completed":
        session_obj = event["data"]["object"]
        metadata = session_obj.get("metadata") or {}
        order_id = metadata.get("order_id") or session_obj.get("client_reference_id")
        product_key = metadata.get("product_key") or settings.billing_product_key
        mode_raw = metadata.get("mode") or "one_time"
        mode = BillingMode.ONE_TIME if mode_raw == BillingMode.ONE_TIME.value else BillingMode.SUBSCRIPTION

        if not order_id:
            return {"ok": True}

        order = storage.get_billing_order_by_order_id(order_id)
        if order and order.status != BillingStatus.PAID:
            storage.mark_billing_order_paid(order, provider_payment_id=session_obj.get("payment_intent"))
            _grant_entitlement(storage, user_db_id=order.user_id, mode=order.mode, product_key=product_key)

    return {"ok": True}


@router.post("/webhooks/liqpay")
async def liqpay_webhook(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = form.get("data")
    signature = form.get("signature")
    if not data or not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing data/signature")

    if not (settings.liqpay_public_key and settings.liqpay_private_key):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LiqPay is not configured")

    expected_src = settings.liqpay_private_key + str(data) + settings.liqpay_private_key
    expected_sig = base64.b64encode(hashlib.sha1(expected_src.encode("utf-8")).digest()).decode("ascii")
    if not hmac.compare_digest(expected_sig, str(signature)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    try:
        payload_json = base64.b64decode(str(data)).decode("utf-8")
        payload = json.loads(payload_json)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid data payload")

    storage = DatabaseStorage(db)
    storage.record_billing_event(
        BillingEvent(provider=BillingProvider.LIQPAY, event_id=str(payload.get("payment_id") or ""), order_id=str(payload.get("order_id") or ""), payload=json.dumps(payload))
    )

    order_id = str(payload.get("order_id") or "")
    status_raw = str(payload.get("status") or "")

    # LiqPay marks success as 'success' (and can send 'sandbox' in test)
    paid = status_raw in {"success", "sandbox"}

    if paid and order_id:
        order = storage.get_billing_order_by_order_id(order_id)
        if order and order.status != BillingStatus.PAID:
            storage.mark_billing_order_paid(order, provider_payment_id=str(payload.get("payment_id") or ""))
            _grant_entitlement(storage, user_db_id=order.user_id, mode=order.mode, product_key=order.product_key)

    return {"ok": True}
