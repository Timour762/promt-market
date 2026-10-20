from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Integer, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("user_id", "prompt_id", name="uq_order_user_prompt"), CheckConstraint("status IN ('pending','awaiting_confirmation','paid','test_granted','sandbox_paid')",name="ck_order_status"), CheckConstraint("price_minor >= 0",name="ck_order_price"))
    id: Mapped[UUID] = mapped_column(primary_key=True,default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"),index=True)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.id"))
    version_id: Mapped[int] = mapped_column(ForeignKey("prompt_versions.id"))
    title: Mapped[str] = mapped_column(String(200))
    price_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(32),default="pending",server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
