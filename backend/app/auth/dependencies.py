from typing import Annotated
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import get_session
from app.auth.models import Session, User
from app.auth.security import SESSION_COOKIE, token_hash

Database = Annotated[AsyncSession, Depends(get_session)]

async def current_user(request: Request, db: Database) -> User:
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token or len(token) > 128:
        raise HTTPException(status_code=401, detail="Войдите в аккаунт")
    user = await db.scalar(select(User).join(Session, Session.user_id == User.id).options(selectinload(User.role)).where(Session.token_hash == token_hash(token), Session.expires_at > datetime.now(timezone.utc), User.status == "active"))
    if user is None:
        raise HTTPException(status_code=401, detail="Войдите в аккаунт")
    return user

CurrentUser = Annotated[User, Depends(current_user)]

async def admin_user(user: CurrentUser) -> User:
    if user.role.code != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    return user
