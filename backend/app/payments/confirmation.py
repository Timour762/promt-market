from uuid import UUID
from fastapi import HTTPException
from app.payments.sber import call
from app.admin.models import AuditLog

async def confirm_payment(db, order, payment, *, actor_id=None, bank_order_id=None, source="manual"):
    # Caller must hold the order row lock, shared by manual checks and callbacks.
    lookup_id=payment.bank_order_id or bank_order_id
    result=await call("getOrderStatusExtended.do",{"orderId":lookup_id} if lookup_id else {"orderNumber":order.id.hex})
    if str(result.get("errorCode","0"))!="0":
        raise HTTPException(502,"Банк пока не подтвердил состояние платежа")
    if str(result.get("orderNumber"))!=order.id.hex or str(result.get("amount"))!=str(order.price_minor) or str(result.get("currency"))!="643" or order.currency!="RUB":
        raise HTTPException(409,"Данные банка не совпали с заказом. Доступ не изменён.")
    if bank_order_id and payment.bank_order_id and bank_order_id!=payment.bank_order_id:
        raise HTTPException(409,"Идентификатор платежа не совпал")
    # Some gateway responses carry mdOrder inside attributes instead of orderId.
    returned_id=result.get("orderId")
    attributes=result.get("attributes",[])
    if not returned_id and isinstance(attributes,list):
        returned_id=next((item.get("value") for item in attributes if isinstance(item,dict) and item.get("name")=="mdOrder"),None)
    if returned_id:
        try: returned_id=str(UUID(returned_id))
        except (ValueError,TypeError,AttributeError):raise HTTPException(502,"Некорректный ответ банка") from None
        if lookup_id and returned_id!=lookup_id:raise HTTPException(409,"Идентификатор банка не совпал")
    if not payment.bank_order_id and (lookup_id or returned_id):
        payment.bank_order_id=lookup_id or returned_id
    before=order.status
    if str(result.get("orderStatus"))=="2" and str(result.get("actionCode"))=="0":
        payment.status="succeeded"
        if order.status=="pending":order.status="sandbox_paid"
    elif str(result.get("orderStatus")) in {"3","4","6"}:
        payment.status="canceled"
        if order.status=="sandbox_paid":order.status="pending"
    if before!=order.status:
        db.add(AuditLog(actor_id=actor_id,action="order.sandbox_payment_confirmed" if order.status=="sandbox_paid" else "order.sandbox_access_revoked",entity_id=str(order.id),details={"source":"sber_sandbox","trigger":source,"real_payment":False}))
    await db.commit()
    return {"status":order.status,"mode":"sandbox","message":"Тестовая оплата подтверждена" if order.status=="sandbox_paid" else "Банк пока не подтвердил оплату"}
