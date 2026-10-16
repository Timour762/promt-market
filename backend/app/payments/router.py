from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from app.auth.dependencies import Database,CurrentUser
from app.auth.security import require_csrf
from app.orders.models import Order
from app.payments.models import Payment
from app.payments.sber import call,enabled,safe_form_url
from app.core.config import get_settings
from app.admin.models import AuditLog
router=APIRouter(prefix="/me/orders",tags=["sandbox payments"])
async def locked(order_id,db,user):
    order=await db.scalar(select(Order).where(Order.id==order_id,Order.user_id==user.id).with_for_update())
    if order is None:raise HTTPException(404,"Заказ не найден")
    return order
@router.get("/{order_id}/payment")
async def info(order_id:UUID,db:Database,user:CurrentUser):
    order=await locked(order_id,db,user)
    return {"enabled":enabled(),"mode":"sandbox","status":order.status}
@router.post("/{order_id}/payment",dependencies=[Depends(require_csrf)])
async def start(order_id:UUID,db:Database,user:CurrentUser):
    if not enabled():raise HTTPException(503,"Тестовый эквайринг Сбера ещё не подключён")
    order=await locked(order_id,db,user)
    if order.status!="pending":raise HTTPException(409,"Доступ по этому заказу уже открыт")
    if order.currency!="RUB" or order.price_minor<=0:raise HTTPException(409,"Для тестовой оплаты нужна положительная сумма в рублях")
    payment=await db.scalar(select(Payment).where(Payment.order_id==order.id))
    if payment:
        if payment.status=="canceled":raise HTTPException(409,"Тестовый платёж отменён. Повторная оплата пока не поддерживается.")
        if payment.form_url:return {"url":payment.form_url,"mode":"sandbox"}
        raise HTTPException(409,"Запрос уже отправлялся. Проверьте статус, чтобы восстановить результат без повторного списания.")
    payment=Payment(order_id=order.id,status="created")
    db.add(payment)
    # Persist intent before contacting the bank, including in an ambiguous timeout.
    await db.commit()
    await locked(order_id,db,user)
    result=await call("register.do",{"orderNumber":order.id.hex,"amount":order.price_minor,"currency":"643","returnUrl":get_settings().public_web_url+f"/account/orders/{order.id}","description":f"Test order {order.id.hex}","language":"ru"})
    url=safe_form_url(result.get("formUrl"))
    try: bank_id=str(UUID(result.get("orderId","")))
    except (ValueError,TypeError,AttributeError):bank_id=None
    if str(result.get("errorCode","0"))!="0" or not url or not bank_id:
        raise HTTPException(502,"Шлюз не вернул платёжную ссылку. Проверьте статус заказа или настройки эквайринга.")
    payment.bank_order_id=bank_id;payment.form_url=url;payment.status="pending"
    await db.commit()
    return {"url":url,"mode":"sandbox"}
@router.post("/{order_id}/payment/check",dependencies=[Depends(require_csrf)])
async def check(order_id:UUID,db:Database,user:CurrentUser):
    order=await locked(order_id,db,user)
    payment=await db.scalar(select(Payment).where(Payment.order_id==order.id))
    if payment is None:raise HTTPException(409,"Тестовый платёж ещё не создавался")
    from app.payments.confirmation import confirm_payment
    return await confirm_payment(db,order,payment,actor_id=user.id)
