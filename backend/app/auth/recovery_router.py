from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from starlette.concurrency import run_in_threadpool
from app.auth.dependencies import CurrentUser, Database
from app.auth.mail import deliver_local_mail, enqueue_mail
from app.auth.models import User
from app.auth.recovery_models import AuthToken
from app.auth.recovery import issue_link, locked_token_user, revoke_recovery
from app.auth.schemas import EmailRequest, TokenRequest, PasswordReset
from app.auth.security import SESSION_COOKIE, limit_attempts, password_hasher, require_csrf
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["account recovery"], dependencies=[Depends(require_csrf)])

def no_store(response: Response):
    response.headers["Cache-Control"] = "no-store"

@router.post("/resend-verification")
async def resend_verification(request: Request, response: Response, background: BackgroundTasks, db: Database, current: CurrentUser):
    if not current.email:
        raise HTTPException(status_code=400, detail="Для подтверждения нужен email. У этого локального аккаунта он не указан.")
    limit_attempts(request, "verify:" + current.email)
    user = await db.scalar(select(User).where(User.id == current.id, User.status == "active").with_for_update())
    if user is not None and user.email_verified_at is None:
        await issue_link(db, user, "verify_email")
        await db.commit()
        background.add_task(deliver_local_mail)
    no_store(response)
    return {"message": "Если email ещё не подтверждён, письмо подготовлено. Проверьте настроенный канал доставки писем."}

@router.post("/verify-email")
async def verify_email(data: TokenRequest, request: Request, response: Response, db: Database):
    limit_attempts(request)
    user = await locked_token_user(db, data.token, "verify_email")
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
    await db.execute(delete(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == "verify_email"))
    await db.commit()
    no_store(response)
    return {"message": "Email подтверждён."}

@router.post("/forgot-password")
async def forgot_password(data: EmailRequest, request: Request, response: Response, background: BackgroundTasks, db: Database):
    limit_attempts(request, "recovery:" + str(data.email))
    user = await db.scalar(select(User).where(User.email == str(data.email), User.status == "active").with_for_update())
    if user is not None:
        await issue_link(db, user, "reset_password")
        await db.commit()
        background.add_task(deliver_local_mail)
    no_store(response)
    # Same response for existing and unknown addresses.
    return {"message": "Если аккаунт с таким email существует, письмо для восстановления подготовлено. Проверьте почту или локальную папку писем в режиме разработки."}

@router.post("/reset-password")
async def reset_password(data: PasswordReset, request: Request, response: Response, background: BackgroundTasks, db: Database):
    limit_attempts(request)
    user = await locked_token_user(db, data.token, "reset_password")
    user.password_hash = await run_in_threadpool(password_hasher.hash, data.password)
    await revoke_recovery(db, user)
    enqueue_mail(db, user.email, "Пароль ПромтМаркета изменён", "Пароль изменён. Все прежние сеансы завершены. Если вы не меняли пароль, запросите восстановление доступа.")
    await db.commit()
    background.add_task(deliver_local_mail)
    no_store(response)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=get_settings().cookie_secure, httponly=True, samesite="lax")
    return {"message": "Пароль изменён. Войдите с новым паролем."}
