from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import get_settings
from app.catalog.router import router
from app.auth.router import router as auth_router
from app.auth.recovery_router import router as recovery_router
from app.db.session import engine, SessionFactory
from app.admin.router import router as admin_router
from app.orders.router import router as orders_router
from app.payments.router import router as payments_router
from app.payments.webhook import router as webhook_router
from app.payments.recipient import router as recipient_router
from app.payments.manual import router as manual_payment_router
from app.payments.platega_router import router as platega_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(title=get_settings().app_name, version="0.5.0", lifespan=lifespan)
app.include_router(router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(recovery_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(recipient_router, prefix="/api/v1")
app.include_router(manual_payment_router, prefix="/api/v1")
app.include_router(platega_router, prefix="/api/v1")

@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Catalog storage is temporarily unavailable"})

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "storage": "postgresql", "payments": "not_connected"}

@app.get("/ready", tags=["system"])
async def ready():
    async with SessionFactory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Never reflect submitted passwords or cookies in validation responses.
    errors = [{"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors}, headers={"Cache-Control": "no-store"})

@app.middleware("http")
async def private_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/api/v1/admin", "/api/v1/auth", "/api/v1/payments")) or request.url.path.startswith("/api/v1/me"):
        response.headers["Cache-Control"] = "no-store"
    return response
