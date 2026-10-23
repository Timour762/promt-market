from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from app.admin.models import AuditLog
from app.auth.dependencies import CurrentUser, Database, admin_user
from app.auth.models import User
from app.auth.security import require_csrf
from app.core.config import get_settings
from app.orders.models import Order
from app.orders.router import summary
from app.payments.manual_models import ManualPayment
from app.payments.models import Payment
from app.payments.platega_models import PlategaPayment
from app.payments.recipient import PaymentRecipient

router = APIRouter(tags=["manual payments"])
Admin = Annotated[User, Depends(admin_user)]


class PaymentAction(BaseModel):
    model_config = ConfigDict(extra="forbid")


def require_sales():
    settings = get_settings()
    if settings.app_env == "production" and not settings.legal_ready:
        raise HTTPException(503, "Продажи ещё не открыты. Личный кабинет доступен.")


async def own_order(order_id, db, user, *, lock=False):
    query = select(Order).where(Order.id == order_id, Order.user_id == user.id)
    order = await db.scalar(query.with_for_update() if lock else query)
    if order is None:
        raise HTTPException(404, "Заказ не найден")
    return order


def payment_status(order):
    return {"order_id": str(order.id), "status": order.status}


@router.get("/me/orders/{order_id}/manual-payment/status")
async def status(order_id: UUID, db: Database, user: CurrentUser):
    return payment_status(await own_order(order_id, db, user))


@router.get("/me/orders/{order_id}/manual-payment")
async def details(order_id: UUID, db: Database, user: CurrentUser):
    order = await own_order(order_id, db, user)
    payment = await db.get(ManualPayment, order.id)
    recipient = None
    if payment is not None and order.status == "awaiting_confirmation":
        key = get_settings().payment_details_encryption_key
        if not key:
            raise HTTPException(503, "Реквизиты временно недоступны. Обратитесь в поддержку.")
        try:
            card = Fernet(key.get_secret_value().encode()).decrypt(payment.encrypted_card.encode()).decode()
        except InvalidToken:
            raise HTTPException(503, "Реквизиты временно недоступны. Обратитесь в поддержку.") from None
        recipient = {"recipient_name": payment.recipient_name, "bank_name": payment.bank_name, "card_number": card}
    return {**payment_status(order), "recipient": recipient}


@router.post("/me/orders/{order_id}/manual-payment", dependencies=[Depends(require_csrf)])
async def start(order_id: UUID, data: PaymentAction, db: Database, user: CurrentUser):
    require_sales()
    order = await own_order(order_id, db, user, lock=True)
    if order.status != "pending":
        return payment_status(order)
    if order.currency != "RUB" or order.price_minor <= 0:
        raise HTTPException(409, "Для оплаты нужна положительная сумма в рублях")
    if await db.scalar(select(Payment.id).where(Payment.order_id == order.id)) or await db.scalar(select(PlategaPayment.id).where(PlategaPayment.order_id == order.id)):
        raise HTTPException(409, "По заказу уже начата тестовая оплата. Обратитесь к администратору.")
    recipient = await db.scalar(select(PaymentRecipient).where(PaymentRecipient.id == 1).with_for_update())
    if recipient is None or not get_settings().payment_details_encryption_key:
        raise HTTPException(503, "Получатель ещё не указал реквизиты. Попробуйте оплатить позже.")
    # Keep the exact encrypted recipient snapshot shown to this buyer, even if settings change.
    db.add(ManualPayment(order_id=order.id, recipient_name=recipient.recipient_name,
                         bank_name=recipient.bank_name, encrypted_card=recipient.encrypted_card,
                         card_last4=recipient.card_last4, recipient_revision=recipient.revision))
    order.status = "awaiting_confirmation"
    db.add(AuditLog(actor_id=user.id, action="order.manual_payment_requested", entity_id=str(order.id),
                    details={"recipient_revision": recipient.revision, "price_minor": order.price_minor}))
    await db.commit()
    return payment_status(order)


@router.get("/admin/orders/pending-payments")
async def pending(db: Database, actor: Admin, offset: int = Query(default=0, ge=0)):
    query = (select(Order, User, ManualPayment).join(User, User.id == Order.user_id)
             .join(ManualPayment, ManualPayment.order_id == Order.id)
             .where(Order.status == "awaiting_confirmation"))
    total = await db.scalar(select(func.count()).select_from(Order).where(Order.status == "awaiting_confirmation"))
    rows = (await db.execute(query.order_by(ManualPayment.requested_at, Order.id).offset(offset).limit(50))).all()
    return {"total": total, "items": [
        {**summary(order), "customer_name": user.name, "customer_contact": user.email or user.username or "",
         "requested_at": payment.requested_at, "recipient_name": payment.recipient_name,
         "bank_name": payment.bank_name, "masked_card": "•••• •••• •••• " + payment.card_last4}
        for order, user, payment in rows
    ]}


@router.post("/admin/orders/{order_id}/confirm-payment", dependencies=[Depends(require_csrf)])
async def confirm(order_id: UUID, data: PaymentAction, db: Database, actor: Admin):
    require_sales()
    order = await db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(404, "Заказ не найден")
    payment = await db.get(ManualPayment, order.id)
    if payment is None:
        raise HTTPException(409, "По заказу нет ожидающего перевода")
    if order.status == "paid" and payment.confirmed_at is not None:
        return summary(order)
    if order.status != "awaiting_confirmation":
        raise HTTPException(409, "Заказ уже не ожидает подтверждения")
    order.status = "paid"
    payment.confirmed_at = datetime.now(timezone.utc)
    payment.confirmed_by = actor.id
    db.add(AuditLog(actor_id=actor.id, action="order.manual_payment_confirmed", entity_id=str(order.id),
                    details={"price_minor": order.price_minor, "currency": order.currency,
                             "recipient_revision": payment.recipient_revision}))
    await db.commit()
    return summary(order)
