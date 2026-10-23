from uuid import UUID
from typing import Annotated
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from app.auth.dependencies import Database, CurrentUser, admin_user
from app.auth.models import User
from app.auth.security import require_csrf
from app.catalog.models import Prompt, PromptVersion
from app.orders.models import Order
from app.admin.models import AuditLog
from app.core.config import get_settings

router=APIRouter(tags=["orders"])
Admin=Annotated[User,Depends(admin_user)]
class CreateOrder(BaseModel):
    model_config=ConfigDict(extra="forbid")
    prompt_id: str=Field(min_length=1,max_length=80)
def summary(order):
    return {"id":str(order.id),"prompt_id":order.prompt_id,"title":order.title,"price_minor":order.price_minor,"currency":order.currency,"status":order.status,"created_at":order.created_at}
def test_access_enabled():
    settings=get_settings()
    return settings.local_test_access_enabled and urlparse(settings.public_web_url).hostname in {"localhost","127.0.0.1"} and not settings.cookie_secure
@router.post("/me/orders",dependencies=[Depends(require_csrf)])
async def create(data:CreateOrder,db:Database,user:CurrentUser):
    settings=get_settings()
    if settings.app_env == "production" and not settings.legal_ready:
        raise HTTPException(503,"Продажи ещё не открыты. Личный кабинет доступен.")
    # Serialize retries per purchaser; never accept client prices or status.
    await db.scalar(select(User).where(User.id==user.id).with_for_update())
    existing=await db.scalar(select(Order).where(Order.user_id==user.id,Order.prompt_id==data.prompt_id))
    if existing: return summary(existing)
    prompt=await db.scalar(select(Prompt).where(Prompt.id==data.prompt_id,Prompt.status=="published").with_for_update())
    if prompt is None or prompt.price_minor is None:
        raise HTTPException(409,"Товар пока недоступен для оформления")
    version=await db.scalar(select(PromptVersion).where(PromptVersion.prompt_id==prompt.id).order_by(PromptVersion.version.desc()).limit(1))
    if not version or not version.content.strip(): raise HTTPException(409,"Текст товара ещё не готов")
    order=Order(user_id=user.id,prompt_id=prompt.id,version_id=version.id,title=prompt.title,price_minor=prompt.price_minor,currency=prompt.currency)
    db.add(order);await db.commit();return summary(order)
@router.get("/me/orders")
async def orders(db:Database,user:CurrentUser,offset:int=Query(default=0,ge=0)):
    items=(await db.scalars(select(Order).where(Order.user_id==user.id).order_by(Order.created_at.desc(),Order.id).offset(offset).limit(50))).all()
    return [summary(item) for item in items]
@router.get("/me/orders/{order_id}")
async def order_detail(order_id:UUID,db:Database,user:CurrentUser):
    order=await db.scalar(select(Order).where(Order.id==order_id,Order.user_id==user.id))
    if order is None: raise HTTPException(404,"Заказ не найден")
    return summary(order)
@router.get("/me/library")
async def library(db:Database,user:CurrentUser,offset:int=Query(default=0,ge=0)):
    items=(await db.scalars(select(Order).where(Order.user_id==user.id,Order.status.in_(["paid","test_granted","sandbox_paid"])).order_by(Order.created_at.desc(),Order.id).offset(offset).limit(50))).all()
    return [summary(item) for item in items]
async def own_content(order_id,db,user):
    order=await db.scalar(select(Order).where(Order.id==order_id,Order.user_id==user.id,Order.status.in_(["paid","test_granted","sandbox_paid"])))
    if order is None: raise HTTPException(404,"Промпт не найден в вашей библиотеке")
    version=await db.get(PromptVersion,order.version_id)
    return order,version
@router.get("/me/library/{order_id}")
async def content(order_id:UUID,db:Database,user:CurrentUser):
    order,version=await own_content(order_id,db,user)
    return {**summary(order),"content":version.content,"version":version.version}
@router.get("/me/library/{order_id}/download")
async def download(order_id:UUID,db:Database,user:CurrentUser):
    order,version=await own_content(order_id,db,user)
    return Response(version.content,media_type="text/plain; charset=utf-8",headers={"Content-Disposition":f'attachment; filename="prompt-{order.id}.txt"',"Cache-Control":"no-store"})
@router.get("/admin/orders")
async def admin_orders(db:Database,actor:Admin,offset:int=Query(default=0,ge=0)):
    rows=(await db.execute(select(Order,User).join(User,User.id==Order.user_id).order_by(Order.created_at.desc(),Order.id).offset(offset).limit(50))).all()
    return {"items":[{**summary(order),"customer":user.email or user.username or user.name} for order,user in rows],"test_access_enabled":test_access_enabled()}
@router.post("/admin/orders/{order_id}/test-access",dependencies=[Depends(require_csrf)])
async def grant(order_id:UUID,db:Database,actor:Admin):
    if not test_access_enabled():
        raise HTTPException(403,"Учебный доступ отключён в этой среде")
    order=await db.scalar(select(Order).where(Order.id==order_id).with_for_update())
    if order is None: raise HTTPException(404,"Заказ не найден")
    if order.status=="pending":
        from app.payments.models import Payment
        from app.payments.platega_models import PlategaPayment
        if await db.scalar(select(Payment.id).where(Payment.order_id==order.id)) or await db.scalar(select(PlategaPayment.id).where(PlategaPayment.order_id==order.id)):
            raise HTTPException(409,"По заказу уже начата оплата. Сначала проверьте её статус.")
    if order.status=="pending":
        order.status="test_granted"
        db.add(AuditLog(actor_id=actor.id,action="order.test_access_granted",entity_id=str(order.id),details={"source":"local_test","payment_received":False}))
        await db.commit()
    return summary(order)
