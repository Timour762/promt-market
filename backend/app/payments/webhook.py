import asyncio
import json
from uuid import UUID
from fastapi import APIRouter,Request,HTTPException
from pydantic import BaseModel,Field,ValidationError
from sqlalchemy import select
from app.auth.dependencies import Database
from app.core.config import get_settings
from app.orders.models import Order
from app.payments.models import Payment
from app.payments.sber import enabled
from app.payments.confirmation import confirm_payment

router=APIRouter(prefix="/payments/sber",tags=["Sber callbacks"])
_slots=asyncio.Semaphore(8)
class Notification(BaseModel):
    mdOrder: UUID
    orderNumber: str=Field(min_length=1,max_length=80)
    operation: str=Field(min_length=1,max_length=40)
    status: int=Field(ge=0,le=1)
@router.post("/webhook",include_in_schema=True)
async def webhook(request:Request,db:Database):
    if not get_settings().sber_webhook_enabled or not enabled():
        raise HTTPException(503,"Sber sandbox callbacks are not configured")
    if not request.headers.get("content-type","").split(";",1)[0].strip().lower()=="application/json":
        raise HTTPException(415,"Expected JSON callback")
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>8192:raise HTTPException(413,"Callback too large")
    try: notification=Notification.model_validate_json(body)
    except (ValidationError,ValueError):raise HTTPException(400,"Invalid Sber callback") from None
    try: order_id=UUID(notification.orderNumber)
    except ValueError: return {"status":"ignored"}
    # Unknown order/payment IDs never trigger a request to the bank.
    candidate=await db.scalar(select(Payment.order_id).where(Payment.order_id==order_id))
    if candidate is None:return {"status":"ignored"}
    try:await asyncio.wait_for(_slots.acquire(),timeout=0.1)
    except TimeoutError:raise HTTPException(503,"Retry callback later",headers={"Retry-After":"60"}) from None
    try:
        order=await db.scalar(select(Order).where(Order.id==order_id).with_for_update())
        payment=await db.scalar(select(Payment).where(Payment.order_id==order_id))
        bank_id=str(notification.mdOrder)
        if order is None or payment is None:return {"status":"ignored"}
        if payment.bank_order_id and payment.bank_order_id!=bank_id:
            return {"status":"ignored"}
        # The notification is only a trigger. Its status/operation never grant access.
        await confirm_payment(db,order,payment,bank_order_id=bank_id,source="webhook")
        return {"status":"ok"}
    finally:_slots.release()
