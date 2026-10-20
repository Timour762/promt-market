from datetime import datetime
from typing import Annotated
from cryptography.fernet import Fernet
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field,SecretStr,field_validator
from sqlalchemy import CheckConstraint,DateTime,Integer,String,Text,func,select,text
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
from app.auth.dependencies import Database,admin_user
from app.auth.models import User
from app.auth.security import require_csrf
from app.admin.models import AuditLog
from app.core.config import get_settings

class PaymentRecipient(Base):
    __tablename__="payment_recipient"
    __table_args__=(CheckConstraint("id = 1",name="ck_recipient_singleton"),CheckConstraint("revision > 0",name="ck_recipient_revision"))
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    recipient_name:Mapped[str]=mapped_column(String(100))
    bank_name:Mapped[str]=mapped_column(String(100))
    encrypted_card:Mapped[str]=mapped_column(Text)
    card_last4:Mapped[str]=mapped_column(String(4))
    revision:Mapped[int]=mapped_column(Integer,default=1)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

class RecipientEdit(BaseModel):
    model_config=ConfigDict(extra="forbid")
    recipient_name:str=Field(min_length=1,max_length=100)
    bank_name:str=Field(min_length=1,max_length=100)
    revision:int=Field(ge=0,strict=True)
    card_number:SecretStr|None=None
    @field_validator("recipient_name","bank_name",mode="before")
    @classmethod
    def trim(cls,value):return value.strip() if isinstance(value,str) else value
    @field_validator("card_number",mode="before")
    @classmethod
    def validate_card(cls,value):
        if value is None or value=="":return None
        if not isinstance(value,str) or len(value)>40:raise ValueError("Введите номер карты")
        number=value.replace(" ","").replace("-","")
        if not number.isascii() or not number.isdigit() or not 16<=len(number)<=19:
            raise ValueError("Номер карты должен содержать от 16 до 19 цифр")
        digits=[int(char) for char in number]
        checksum=sum((digit*2-9 if digit*2>9 else digit*2) if index%2==1 else digit for index,digit in enumerate(reversed(digits)))
        if checksum%10 or len(set(number))==1:raise ValueError("Проверьте номер карты")
        return number

Admin=Annotated[User,Depends(admin_user)]
router=APIRouter(prefix="/admin/payment-details",tags=["admin payment details"],dependencies=[Depends(admin_user)])
def public_details(row):
    if row is None:return {"configured":False,"recipient_name":"","bank_name":"","masked_card":None,"revision":0}
    return {"configured":True,"recipient_name":row.recipient_name,"bank_name":row.bank_name,"masked_card":"•••• •••• •••• "+row.card_last4,"revision":row.revision}
@router.get("")
async def get_details(db:Database):return public_details(await db.get(PaymentRecipient,1))
@router.patch("",dependencies=[Depends(require_csrf)])
async def save_details(data:RecipientEdit,db:Database,actor:Admin):
    # Serialize singleton creation as well as later updates, including multiple admins.
    await db.execute(text("SELECT pg_advisory_xact_lock(178521093)"))
    row=await db.scalar(select(PaymentRecipient).where(PaymentRecipient.id==1).with_for_update())
    if data.revision!=(row.revision if row else 0):
        raise HTTPException(409,"Реквизиты изменены в другой вкладке. Обновите страницу перед сохранением.")
    if row is None and data.card_number is None:raise HTTPException(422,"Для первого сохранения введите номер карты")
    encrypted=None
    if data.card_number:
        key=get_settings().payment_details_encryption_key
        if not key:raise HTTPException(503,"Защищённое хранение реквизитов не настроено")
        encrypted=Fernet(key.get_secret_value().encode()).encrypt(data.card_number.get_secret_value().encode()).decode()
    if row is None:
        row=PaymentRecipient(id=1,recipient_name=data.recipient_name,bank_name=data.bank_name,encrypted_card=encrypted,card_last4=data.card_number.get_secret_value()[-4:],revision=1)
        db.add(row)
    else:
        row.recipient_name=data.recipient_name;row.bank_name=data.bank_name;row.revision+=1
        if data.card_number:
            row.encrypted_card=encrypted;row.card_last4=data.card_number.get_secret_value()[-4:]
    db.add(AuditLog(actor_id=actor.id,action="payment.recipient_updated",entity_id="shop",details={"card_changed":bool(data.card_number),"revision":row.revision}))
    await db.commit()
    return public_details(row)
