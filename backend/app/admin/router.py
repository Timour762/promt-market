from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.auth.dependencies import Database, admin_user
from app.auth.models import User
from app.auth.security import require_csrf
from app.catalog.models import Category, Prompt, PromptVersion
from app.admin.models import AuditLog
from app.admin.schemas import PromptCreate, PromptEdit, StatusChange

Admin = Annotated[User, Depends(admin_user)]
router = APIRouter(prefix="/admin", tags=["administration"], dependencies=[Depends(admin_user)])

async def latest_version(db: Database, prompt_id: str):
    return await db.scalar(select(PromptVersion).where(PromptVersion.prompt_id == prompt_id).order_by(PromptVersion.version.desc()).limit(1))

def summary(prompt: Prompt):
    return {"id": prompt.id, "title": prompt.title, "category_id": prompt.category_id, "category": prompt.category.name, "description": prompt.description, "result": prompt.result, "symbol": prompt.symbol, "price_minor": prompt.price_minor, "currency": prompt.currency, "status": prompt.status, "revision": prompt.revision}

async def detail(db: Database, prompt: Prompt):
    version = await latest_version(db, prompt.id)
    return {**summary(prompt), "content": version.content if version else "", "content_version": version.version if version else 0}

async def locked_prompt(db: Database, prompt_id: str, revision: int):
    prompt = await db.scalar(select(Prompt).options(selectinload(Prompt.category)).where(Prompt.id == prompt_id).with_for_update())
    if prompt is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    if prompt.revision != revision:
        raise HTTPException(status_code=409, detail="Товар уже изменён в другой вкладке. Скопируйте свои правки и обновите страницу.")
    return prompt

@router.get("/dashboard")
async def dashboard(db: Database):
    counts = dict((await db.execute(select(Prompt.status,func.count()).group_by(Prompt.status))).all())
    return {"prompts": sum(counts.values()), "published": counts.get("published",0), "draft": counts.get("draft",0), "archived": counts.get("archived",0)}

@router.get("/categories")
async def categories(db: Database):
    items = (await db.scalars(select(Category).order_by(Category.name))).all()
    return [{"id": item.id, "name": item.name, "slug": item.slug} for item in items]

@router.get("/prompts")
async def list_prompts(db: Database, q: str = Query(default="", max_length=200), status: Literal["draft","published","archived"] | None = None, offset: int = Query(default=0,ge=0), limit: int = Query(default=50,ge=1,le=100)):
    conditions = []
    if status:
        conditions.append(Prompt.status == status)
    if q.strip():
        conditions.append(func.strpos(func.lower(Prompt.title),q.strip().lower()) > 0)
    total = await db.scalar(select(func.count()).select_from(Prompt).where(*conditions))
    items = (await db.scalars(select(Prompt).options(selectinload(Prompt.category)).where(*conditions).order_by(Prompt.created_at.desc(),Prompt.id).offset(offset).limit(limit))).all()
    return {"items":[summary(item) for item in items],"total":total,"offset":offset,"limit":limit}

@router.get("/prompts/{prompt_id}")
async def get_prompt(prompt_id: str, db: Database):
    prompt = await db.scalar(select(Prompt).options(selectinload(Prompt.category)).where(Prompt.id == prompt_id))
    if prompt is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return await detail(db,prompt)

@router.post("/prompts", status_code=201, dependencies=[Depends(require_csrf)])
async def create_prompt(data: PromptCreate, db: Database, actor: Admin):
    category = await db.get(Category,data.category_id)
    if category is None:
        raise HTTPException(status_code=400,detail="Выберите существующую категорию")
    values = data.model_dump(exclude={"content"})
    prompt = Prompt(**values,category=category,status="draft",currency="RUB",revision=1)
    db.add(prompt)
    try:
        await db.flush()
        if data.content.strip():
            db.add(PromptVersion(prompt_id=prompt.id,version=1,content=data.content))
        db.add(AuditLog(actor_id=actor.id,action="prompt.created",entity_id=prompt.id,details={"revision":1,"content_present":bool(data.content.strip())}))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409,detail="Такой адрес товара уже существует. Выберите другой.")
    return await detail(db,prompt)

@router.patch("/prompts/{prompt_id}", dependencies=[Depends(require_csrf)])
async def update_prompt(prompt_id: str, data: PromptEdit, db: Database, actor: Admin):
    prompt = await locked_prompt(db,prompt_id,data.revision)
    category = await db.get(Category,data.category_id)
    if category is None:
        raise HTTPException(status_code=400,detail="Выберите существующую категорию")
    if prompt.status == "published" and (data.price_minor is None or not data.content.strip()):
        raise HTTPException(status_code=400,detail="Для опубликованного товара нужны цена и полный текст. Сначала переведите его в черновик.")
    version = await latest_version(db,prompt.id)
    changed = data.content != (version.content if version else "")
    fields = data.model_dump(exclude={"content","revision"})
    for name,value in fields.items():
        setattr(prompt,name,value)
    prompt.category = category
    if changed:
        db.add(PromptVersion(prompt_id=prompt.id,version=(version.version+1 if version else 1),content=data.content))
    prompt.revision += 1
    db.add(AuditLog(actor_id=actor.id,action="prompt.updated",entity_id=prompt.id,details={"revision":prompt.revision,"content_changed":changed,"fields":list(fields)}))
    await db.commit()
    return await detail(db,prompt)

@router.post("/prompts/{prompt_id}/{action}", dependencies=[Depends(require_csrf)])
async def change_status(prompt_id: str, action: Literal["publish","archive","draft"], data: StatusChange, db: Database, actor: Admin):
    prompt = await locked_prompt(db,prompt_id,data.revision)
    target = {"publish":"published","archive":"archived","draft":"draft"}[action]
    if target == "published":
        version = await latest_version(db,prompt.id)
        if prompt.price_minor is None or version is None or not version.content.strip():
            raise HTTPException(status_code=400,detail="Перед публикацией сохраните цену и полный текст промпта.")
    if prompt.status != target:
        previous = prompt.status
        prompt.status = target
        prompt.revision += 1
        db.add(AuditLog(actor_id=actor.id,action="prompt.status_changed",entity_id=prompt.id,details={"from":previous,"to":target,"revision":prompt.revision}))
        await db.commit()
    return await detail(db,prompt)

@router.get("/audit")
async def audit(db: Database, offset: int = Query(default=0,ge=0), limit: int = Query(default=50,ge=1,le=100)):
    total = await db.scalar(select(func.count()).select_from(AuditLog))
    entries = (await db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc(),AuditLog.id).offset(offset).limit(limit))).all()
    return {"items":[{"id":str(item.id),"actor_id":str(item.actor_id) if item.actor_id else None,"action":item.action,"entity_id":item.entity_id,"details":item.details,"created_at":item.created_at.isoformat()} for item in entries],"total":total,"offset":offset,"limit":limit}


@router.get("/payments/setup")
async def payment_setup():
    from app.core.config import get_settings
    from app.payments.platega import configured, enabled, public_url_ready
    settings = get_settings()
    return {
        "provider": "platega",
        "live_enabled": enabled(),
        "enabled_in_settings": settings.platega_enabled,
        "merchant_id_configured": bool(settings.platega_merchant_id),
        "secret_configured": bool(settings.platega_secret and settings.platega_secret.get_secret_value().strip()),
        "credentials_configured": configured(),
        "public_url_configured": public_url_ready(),
        "connection_verified": False,
        "automatic_confirmation_enabled": enabled(),
        "webhook_handler_available": True,
        "webhook_path": "/api/payments/platega/webhook",
        "webhook_url": settings.public_web_url + "/api/payments/platega/webhook" if public_url_ready() else None,
        "checkout_currency": "RUB",
        "settlement_currency": "USDT",
        "payout_configuration": "platega_account",
    }
