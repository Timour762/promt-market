import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from app.catalog.schemas import PublicPrompt

router = APIRouter(prefix="/prompts", tags=["catalog"])
CATALOG = [PublicPrompt.model_validate(item) for item in json.loads(Path(__file__).with_name("data.json").read_text(encoding="utf-8-sig"))]

@router.get("", response_model=list[PublicPrompt])
async def list_prompts(q: str = Query(default="", max_length=200), category: str | None = None):
    query = q.casefold().strip()
    return [p for p in CATALOG if (not category or p.category == category) and (not query or query in f"{p.title} {p.description} {p.category}".casefold())]

@router.get("/{prompt_id}", response_model=PublicPrompt)
async def get_prompt(prompt_id: str):
    for prompt in CATALOG:
        if prompt.id == prompt_id:
            return prompt
    raise HTTPException(status_code=404, detail="Prompt not found")

