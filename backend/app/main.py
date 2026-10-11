from fastapi import FastAPI
from app.core.config import get_settings
from app.catalog.router import router

app = FastAPI(title=get_settings().app_name, version="0.1.0")
app.include_router(router, prefix="/api/v1")

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "storage": "static_catalog", "payments": "not_connected"}
