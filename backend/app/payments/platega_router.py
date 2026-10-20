import asyncio
from datetime import datetime, timezone
import hmac
from typing import Annotated
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from app.admin.models import AuditLog
from app.auth.dependencies import CurrentUser, Database, admin_user
from app.auth.models import User
from app.auth.security import require_csrf
from app.core.config import get_settings
from app.orders.models import Order
from app.payments.models import Payment
from app.payments.manual_models import ManualPayment
from app.payments.platega_models import PlategaPayment
from app.payments.platega import TERMINAL, call, configured, enabled, safe_checkout_url, verify

router = APIRouter(tags=["Platega payments"])
Admin = Annotated[User, Depends(admin_user)]
_callback_slots = asyncio.Semaphore(8)


class PaymentAction(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Notification(BaseModel):
    id: UUID
    status: str = Field(max_length=32)
    payload: str | None = Field(default=None, max_length=100)


async def own_order(order_id, db, user, *, lock=False):
    query = select(Order).where(Order.id == order_id, Order.user_id == user.id)
    order = await db.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
    if order is None:
        raise HTTPException(404, "Заказ не найден")
    return order


async def latest_payment(db, order_id):
    return await db.scalar(select(PlategaPayment).where(PlategaPayment.order_id == order_id)
                           .order_by(PlategaPayment.created_at.desc(), PlategaPayment.id.desc()).limit(1))


def state(order, payment):
    return {"order_id": str(order.id), "status": order.status, "provider": "platega", "enabled": enabled(),
            "provider_status": payment.status if payment else None,
            "checkout_url": safe_checkout_url(payment.checkout_url) if payment and payment.status == "PENDING" and order.status == "pending" else None}


@router.get("/me/orders/{order_id}/platega-payment")
async def info(order_id: UUID, db: Database, user: CurrentUser):
    order = await own_order(order_id, db, user)
    return state(order, await latest_payment(db, order.id))


@router.post("/me/orders/{order_id}/platega-payment", dependencies=[Depends(require_csrf)])
async def start(order_id: UUID, data: PaymentAction, db: Database, user: CurrentUser):
    order = await own_order(order_id, db, user, lock=True)
    payment = await latest_payment(db, order.id)
    if order.status in {"paid", "test_granted", "sandbox_paid"}:
        return state(order, payment)
    if order.status not in {"pending", "awaiting_confirmation"}:
        raise HTTPException(409, "Заказ сейчас недоступен для оплаты")
    if order.currency != "RUB" or order.price_minor <= 0:
        raise HTTPException(409, "Для оплаты нужна положительная сумма в рублях")
    if payment:
        if payment.status == "PENDING" and safe_checkout_url(payment.checkout_url):
            return state(order, payment)
        if payment.status not in TERMINAL:
            raise HTTPException(409, "Создание платежа ещё не подтверждено. Проверьте статус или обратитесь к администратору.")
    if not enabled():
        raise HTTPException(503, "Оплата через Platega ещё не подключена. Попробуйте позже.")
    if await db.scalar(select(Payment.id).where(Payment.order_id == order.id)):
        raise HTTPException(409, "По заказу уже начата тестовая оплата. Обратитесь к администратору.")
    if order.status == "awaiting_confirmation":
        manual = await db.get(ManualPayment, order.id)
        if manual is None or manual.confirmed_at is not None:
            raise HTTPException(409, "Состояние предыдущей оплаты изменилось. Обновите страницу заказа.")
        order.status = "pending"
        db.add(AuditLog(actor_id=user.id, action="order.payment_provider_changed", entity_id=str(order.id),
                        details={"from": "manual", "to": "platega"}))
    payment = PlategaPayment(id=uuid4(), order_id=order.id, status="CREATED")
    db.add(payment)
    # Platega generates transaction IDs and has no documented checkout idempotency key.
    # Save the intent first; an ambiguous timeout must never silently create a second charge.
    await db.commit()
    return_url = get_settings().public_web_url + f"/account/orders/{order.id}/payment"
    try:
        result = await call("POST", "/transaction/process", {
            "paymentMethod": 2, "paymentDetails": {"amount": order.price_minor / 100, "currency": "RUB"},
            "description": f"ПромтМаркет: заказ {order.id}", "return": return_url, "failedUrl": return_url,
            "payload": str(payment.id), "metadata": {"userId": str(user.id)},
        })
    except HTTPException:
        order = await own_order(order_id, db, user, lock=True)
        payment = await db.get(PlategaPayment, payment.id, populate_existing=True)
        if payment.transaction_id is not None:
            return state(order, payment)
        payment.status = "UNKNOWN"
        await db.commit()
        raise
    order = await own_order(order_id, db, user, lock=True)
    payment = await db.get(PlategaPayment, payment.id, populate_existing=True)
    url = safe_checkout_url(result.get("redirect"))
    try:
        transaction_id = UUID(str(result.get("transactionId")))
        merchant_id = UUID(str(result.get("merchantId")))
    except (ValueError, TypeError, AttributeError):
        transaction_id = merchant_id = None
    if not url or not transaction_id or merchant_id != get_settings().platega_merchant_id or result.get("status") != "PENDING":
        payment.status = "UNKNOWN"
        await db.commit()
        raise HTTPException(502, "Не удалось подтвердить создание платежа. Обратитесь к администратору перед повторной оплатой.")
    payment.transaction_id = transaction_id
    payment.checkout_url = url
    if payment.status not in {"CONFIRMED", "CHARGEBACKED"}:
        payment.status = "PENDING"
    db.add(AuditLog(actor_id=user.id, action="order.platega_payment_started", entity_id=str(order.id),
                    details={"transaction_id": str(transaction_id), "price_minor": order.price_minor, "currency": "RUB"}))
    await db.commit()
    return state(order, payment)


@router.post("/me/orders/{order_id}/platega-payment/check", dependencies=[Depends(require_csrf)])
async def check(order_id: UUID, data: PaymentAction, db: Database, user: CurrentUser):
    order = await own_order(order_id, db, user, lock=True)
    payment = await latest_payment(db, order.id)
    if payment is None:
        raise HTTPException(409, "Платёж ещё не создавался")
    await verify(db, order, payment, actor_id=user.id)
    return state(order, payment)


@router.get("/admin/payments/platega")
async def transactions(db: Database, actor: Admin, offset: int = Query(default=0, ge=0)):
    rows = (await db.execute(select(PlategaPayment, Order, User).join(Order, Order.id == PlategaPayment.order_id)
                            .join(User, User.id == Order.user_id)
                            .order_by(PlategaPayment.created_at.desc(), PlategaPayment.id).offset(offset).limit(50))).all()
    return {"items": [{"id": str(payment.id), "order_id": str(order.id), "title": order.title,
                       "customer": user.name, "price_minor": order.price_minor, "currency": order.currency,
                       "status": payment.status, "amount_usdt": str(payment.amount_usdt) if payment.amount_usdt is not None else None,
                       "created_at": payment.created_at} for payment, order, user in rows]}


@router.post("/payments/platega/webhook")
async def webhook(request: Request, db: Database):
    if not configured():
        raise HTTPException(503, "Platega is not configured")
    settings = get_settings()
    supplied_merchant = request.headers.get("X-MerchantId", "").encode()
    supplied_secret = request.headers.get("X-Secret", "").encode()
    if (not hmac.compare_digest(supplied_merchant, str(settings.platega_merchant_id).encode())
            or not hmac.compare_digest(supplied_secret, settings.platega_secret.get_secret_value().encode())):
        raise HTTPException(403, "Invalid callback credentials")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise HTTPException(415, "Expected JSON callback")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 8192:
            raise HTTPException(413, "Callback too large")
    try:
        notification = Notification.model_validate_json(body)
    except (ValidationError, ValueError):
        raise HTTPException(400, "Invalid Platega callback") from None
    candidate = await db.scalar(select(PlategaPayment).where(PlategaPayment.transaction_id == notification.id))
    if candidate is None and notification.payload:
        try:
            attempt_id = UUID(notification.payload)
        except ValueError:
            return {"status": "ignored"}
        candidate = await db.get(PlategaPayment, attempt_id)
        if candidate and candidate.transaction_id is not None:
            candidate = None
    if candidate is None:
        return {"status": "ignored"}
    try:
        await asyncio.wait_for(_callback_slots.acquire(), timeout=.1)
    except TimeoutError:
        raise HTTPException(503, "Retry callback later", headers={"Retry-After": "60"}) from None
    try:
        order = await db.scalar(select(Order).where(Order.id == candidate.order_id).with_for_update())
        payment = await db.get(PlategaPayment, candidate.id, populate_existing=True)
        if payment.transaction_id is not None and payment.transaction_id != notification.id:
            return {"status": "ignored"}
        payment.transaction_id = notification.id
        # The authenticated notification only triggers a server-to-server verification.
        await verify(db, order, payment, force=True)
        return {"status": "ok"}
    finally:
        _callback_slots.release()
