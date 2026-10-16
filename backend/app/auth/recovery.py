import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.mail import enqueue_mail
from app.auth.models import Session, User
from app.auth.recovery_models import AuthToken
from app.auth.security import token_hash
from app.core.config import get_settings

INVALID_LINK = "Ссылка недействительна, уже использована или срок её действия истёк. Запросите новую."

async def issue_link(db: AsyncSession, user: User, purpose: str):
    if not user.email:
        raise HTTPException(status_code=400, detail="У аккаунта не указан email")
    # Caller locks the user row, serializing issuance and consumption.
    await db.execute(delete(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose))
    token = secrets.token_urlsafe(48)
    minutes = 60 if purpose == "verify_email" else 30
    db.add(AuthToken(token_hash=token_hash(token), user_id=user.id, purpose=purpose, expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes)))
    page = "verify-email" if purpose == "verify_email" else "reset-password"
    # The fragment is never sent to the web server or included in access logs.
    link = f"{get_settings().public_web_url}/{page}#token={token}"
    subject = "Подтвердите email в ПромтМаркете" if purpose == "verify_email" else "Восстановление пароля ПромтМаркета"
    text = f"Откройте ссылку и подтвердите действие на странице. Ссылка действует {minutes} минут. Новое письмо отменяет предыдущую ссылку того же типа."
    enqueue_mail(db, user.email, subject, text, link)

async def locked_token_user(db: AsyncSession, token: str, purpose: str) -> User:
    digest = token_hash(token)
    user_id = await db.scalar(select(AuthToken.user_id).where(AuthToken.token_hash == digest, AuthToken.purpose == purpose))
    if user_id is None:
        raise HTTPException(status_code=400, detail=INVALID_LINK)
    # Lock user first in every token-changing operation to avoid lock inversions.
    user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
    entry = await db.scalar(select(AuthToken).where(AuthToken.token_hash == digest, AuthToken.purpose == purpose).with_for_update())
    if user is None or user.status != "active" or entry is None or entry.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail=INVALID_LINK)
    return user

async def revoke_recovery(db: AsyncSession, user: User):
    await db.execute(delete(AuthToken).where(AuthToken.user_id == user.id))
    await db.execute(delete(Session).where(Session.user_id == user.id))
