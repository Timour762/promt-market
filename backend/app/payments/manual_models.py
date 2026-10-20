from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ManualPayment(Base):
    __tablename__ = "manual_payments"

    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    recipient_name: Mapped[str] = mapped_column(String(100))
    bank_name: Mapped[str] = mapped_column(String(100))
    encrypted_card: Mapped[str] = mapped_column(Text)
    card_last4: Mapped[str] = mapped_column(String(4))
    recipient_revision: Mapped[int] = mapped_column(Integer)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
