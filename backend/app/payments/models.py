from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,ForeignKey,String,Text,func
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
class Payment(Base):
    __tablename__="payments"
    id:Mapped[UUID]=mapped_column(primary_key=True,default=uuid4)
    order_id:Mapped[UUID]=mapped_column(ForeignKey("orders.id"),unique=True)
    bank_order_id:Mapped[str|None]=mapped_column(String(36),unique=True,nullable=True)
    form_url:Mapped[str|None]=mapped_column(Text,nullable=True)
    status:Mapped[str]=mapped_column(String(20),default="created")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
