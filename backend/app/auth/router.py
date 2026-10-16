from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool
from app.auth.dependencies import CurrentUser, Database
from app.auth.models import Role, Session, User
from app.auth.schemas import Credentials, PublicUser, Registration
from app.auth.security import CSRF_COOKIE, DUMMY_HASH, SESSION_COOKIE, limit_attempts, new_csrf_token, password_hasher, require_csrf, token_hash, verify_password
from app.auth.service import create_session, public_user, set_session_cookie
from app.core.config import get_settings
from app.auth.recovery import issue_link
from app.auth.mail import deliver_local_mail

router = APIRouter(tags=["auth"])

@router.get("/auth/csrf")
async def csrf(response: Response):
    token = new_csrf_token()
    response.set_cookie(CSRF_COOKIE, token, httponly=True, secure=get_settings().cookie_secure, samesite="strict", path="/", max_age=3600)
    response.headers["Cache-Control"] = "no-store"
    return {"token": token}

@router.post("/auth/register", response_model=PublicUser, status_code=201, dependencies=[Depends(require_csrf)])
async def register(data: Registration, request: Request, response: Response, background: BackgroundTasks, db: Database):
    limit_attempts(request, str(data.email))
    role = await db.scalar(select(Role).where(Role.code == "customer"))
    if role is None:
        raise HTTPException(status_code=503, detail="Регистрация временно недоступна")
    encoded = await run_in_threadpool(password_hasher.hash, data.password)
    user = User(name=data.name, email=str(data.email), password_hash=encoded, role_id=role.id, role=role)
    db.add(user)
    try:
        await db.flush()
        token = await create_session(db, user, request)
        await issue_link(db, user, "verify_email")
        await db.commit()
        background.add_task(deliver_local_mail)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Не удалось зарегистрировать аккаунт. Если он уже есть, войдите.")
    set_session_cookie(response, token)
    return public_user(user)

@router.post("/auth/login", response_model=PublicUser, dependencies=[Depends(require_csrf)])
async def login(data: Credentials, request: Request, response: Response, db: Database):
    limit_attempts(request, str(data.email))
    user = await db.scalar(select(User).options(selectinload(User.role)).where(or_(User.email == str(data.email), User.username == str(data.email))).with_for_update(of=User))
    valid = await run_in_threadpool(verify_password, user.password_hash if user else DUMMY_HASH, data.password)
    if user is None or not valid or user.status != "active":
        raise HTTPException(status_code=401, detail="Неверный логин, email или пароль")
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = await run_in_threadpool(password_hasher.hash, data.password)
    token = await create_session(db, user, request)
    await db.commit()
    set_session_cookie(response, token)
    return public_user(user)

@router.post("/auth/logout", status_code=204, dependencies=[Depends(require_csrf)])
async def logout(request: Request, db: Database):
    token = request.cookies.get(SESSION_COOKIE, "")
    if token and len(token) <= 128:
        await db.execute(delete(Session).where(Session.token_hash == token_hash(token)))
        await db.commit()
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(SESSION_COOKIE, path="/", secure=get_settings().cookie_secure, httponly=True, samesite="lax")
    return response

@router.get("/me", response_model=PublicUser)
async def me(user: CurrentUser, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return public_user(user)
