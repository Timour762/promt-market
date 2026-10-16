from datetime import datetime, timedelta, timezone
import secrets
from fastapi import Request, Response
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import Session, User
from app.auth.schemas import PublicUser
from app.auth.security import SESSION_COOKIE, token_hash
from app.core.config import get_settings

def public_user(user: User) -> PublicUser:
    return PublicUser(id=user.id, name=user.name, email=user.email, username=user.username, role=user.role.code, email_verified=user.email_verified_at is not None)

async def create_session(db: AsyncSession, user: User, request: Request) -> str:
    previous = request.cookies.get(SESSION_COOKIE, "")
    if previous and len(previous) <= 128:
        await db.execute(delete(Session).where(Session.token_hash == token_hash(previous)))
    token = secrets.token_urlsafe(48)
    db.add(Session(token_hash=token_hash(token), user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(days=get_settings().session_days)))
    return token

def set_session_cookie(response: Response, token: str):
    settings = get_settings()
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/", max_age=settings.session_days * 86400)
    response.headers["Cache-Control"] = "no-store"
