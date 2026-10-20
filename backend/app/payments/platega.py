"""Platega RUB checkout. Wallet withdrawals are configured in the merchant's Platega account."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from sqlalchemy import select
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from app.admin.models import AuditLog
from app.core.config import get_settings
from app.payments.platega_models import PlategaPayment

BASE = "https://app.platega.io"
TERMINAL = {"CANCELED", "EXPIRED", "FAILED"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def public_url_ready():
    import ipaddress
    parts = urlsplit(get_settings().public_web_url)
    hostname = (parts.hostname or "").rstrip(".").lower()
    if parts.scheme != "https" or not hostname or hostname in {"localhost", "localhost.localdomain"}:
        return False
    try:
        return ipaddress.ip_address(hostname).is_global
    except ValueError:
        return not hostname.endswith((".localhost", ".local", ".internal"))


def configured():
    settings = get_settings()
    return bool(settings.platega_merchant_id and settings.platega_secret and settings.platega_secret.get_secret_value().strip())


def enabled():
    settings = get_settings()
    return bool(settings.platega_enabled and configured() and (public_url_ready() or settings.app_env == "test"))


def safe_checkout_url(value):
    if not isinstance(value, str) or any(char.isspace() for char in value) or "\\" in value:
        return None
    try:
        parts = urlsplit(value)
        if (parts.scheme == "https" and parts.hostname == "pay.platega.io" and parts.port in (None, 443)
                and not parts.username and not parts.password):
            return value
    except ValueError:
        pass
    return None


async def call(method, path, data=None):
    if not configured():
        raise HTTPException(503, "Оплата через Platega ещё не подключена. Попробуйте позже.")
    settings = get_settings()

    def send():
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode() if data is not None else None
        request = Request(BASE + path, data=body, method=method, headers={
            "X-MerchantId": str(settings.platega_merchant_id),
            "X-Secret": settings.platega_secret.get_secret_value(),
            "Accept": "application/json", "Content-Type": "application/json",
        })
        try:
            with build_opener(NoRedirect()).open(request, timeout=10) as response:
                raw = response.read(262145)
                if len(raw) > 262144:
                    raise ValueError()
                result = json.loads(raw, parse_float=Decimal)
                if not isinstance(result, dict):
                    raise ValueError()
                return result
        except (URLError, TimeoutError, ValueError, OSError):
            raise HTTPException(503, "Platega временно недоступна. Проверьте статус оплаты позже.") from None

    return await run_in_threadpool(send)


def decimal_amount(value):
    try:
        amount = Decimal(str(value))
        if amount.is_finite() and 0 <= amount < Decimal("10000000000000000"):
            return amount
    except (InvalidOperation, ValueError):
        pass
    return None


async def verify(db, order, payment, *, actor_id=None, force=False):
    if payment.transaction_id is None:
        raise HTTPException(409, "Создание платежа не подтверждено. Обратитесь к администратору перед повторной оплатой.")
    now = datetime.now(timezone.utc)
    if not force and payment.checked_at and (now - payment.checked_at).total_seconds() < 5:
        return
    result = await call("GET", f"/transaction/{payment.transaction_id}")
    try:
        transaction_id = UUID(str(result.get("id")))
        merchant_id = UUID(str(result.get("merchantId", result.get("mechantId"))))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(502, "Некорректный ответ Platega. Доступ не изменён.") from None
    details = result.get("paymentDetails")
    amount = decimal_amount(details.get("amount")) if isinstance(details, dict) else None
    if (transaction_id != payment.transaction_id or merchant_id != get_settings().platega_merchant_id
            or amount is None or amount * 100 != order.price_minor
            or details.get("currency") != "RUB" or order.currency != "RUB"
            or result.get("payload") != str(payment.id)):
        raise HTTPException(409, "Данные Platega не совпали с заказом. Доступ не изменён.")
    status = result.get("status")
    if status not in {"PENDING", "CONFIRMED", "CHARGEBACKED", *TERMINAL}:
        raise HTTPException(502, "Platega вернула неизвестный статус. Повторите проверку позже.")
    if payment.status == "CONFIRMED" and status != "CHARGEBACKED":
        status = "CONFIRMED"
    before = order.status
    # A chargeback remains final even if an old confirmation arrives later.
    if payment.status != "CHARGEBACKED":
        payment.status = status
        if status == "CONFIRMED" and order.status == "pending":
            order.status = "paid"
        elif status == "CHARGEBACKED" and order.status == "paid":
            other_confirmed = await db.scalar(select(PlategaPayment.id).where(
                PlategaPayment.order_id == order.id, PlategaPayment.id != payment.id,
                PlategaPayment.status == "CONFIRMED"))
            if other_confirmed is None:
                order.status = "pending"
        payment.amount_usdt = decimal_amount(result.get("amountUsdt"))
        payment.commission_usdt = decimal_amount(result.get("comissionUsdt"))
    payment.checked_at = now
    if before != order.status:
        db.add(AuditLog(actor_id=actor_id,
                        action="order.platega_payment_confirmed" if order.status == "paid" else "order.platega_access_revoked",
                        entity_id=str(order.id), details={"transaction_id": str(payment.transaction_id),
                                                        "price_minor": order.price_minor, "currency": order.currency}))
    await db.commit()
