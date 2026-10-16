from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.catalog.models import Category, Prompt
from app.catalog.schemas import PublicPrompt
from app.db.session import get_session

router = APIRouter(prefix="/prompts", tags=["catalog"])
Session = Annotated[AsyncSession, Depends(get_session)]

def public_prompt(prompt: Prompt) -> PublicPrompt:
    return PublicPrompt(id=prompt.id, title=prompt.title, category=prompt.category.name, description=prompt.description, symbol=prompt.symbol, result=prompt.result, price_minor=prompt.price_minor, currency=prompt.currency)

@router.get("", response_model=list[PublicPrompt])
async def list_prompts(session: Session, q: str = Query(default="", max_length=200), category: str | None = Query(default=None, max_length=120), limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    statement = select(Prompt).join(Prompt.category).options(selectinload(Prompt.category)).where(Prompt.status == "published")
    if category:
        statement = statement.where(Category.name == category)
    query = q.strip().lower()
    if query:
        statement = statement.where(or_(func.strpos(func.lower(Prompt.title), query) > 0, func.strpos(func.lower(Prompt.description), query) > 0, func.strpos(func.lower(Category.name), query) > 0))
    prompts = (await session.scalars(statement.order_by(Prompt.created_at, Prompt.id).limit(limit).offset(offset))).all()
    return [public_prompt(prompt) for prompt in prompts]

@router.get("/{prompt_id}", response_model=PublicPrompt)
async def get_prompt(prompt_id: str, session: Session):
    prompt = await session.scalar(select(Prompt).options(selectinload(Prompt.category)).where(Prompt.id == prompt_id, Prompt.status == "published"))
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return public_prompt(prompt)
