from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PlategaPayment(Base):
    __tablename__ = "platega_payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    transaction_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="CREATED")
    amount_usdt: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    commission_usdt: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
