import argparse
import asyncio
import json
import re
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.catalog.models import Category, Prompt, PromptVersion
from app.db.session import SessionFactory, engine

IDS = ["python", "business", "marketing", "reels", "image", "video"]
CATEGORY_SLUGS = ["programming", "business", "marketing", "social", "images", "video"]

async def seed(content_file: Path | None):
    public = json.loads(Path(__file__).with_name("catalog").joinpath("data.json").read_text(encoding="utf-8-sig"))
    contents = None
    if content_file:
        raw = content_file.read_text(encoding="utf-8-sig")
        headings = ["Senior Python Developer", "Бизнес-план за 30 минут", "Маркетолог уровня PRO", "Генератор вирусных Reels", "AI Image Prompt Architect", "AI Video Director"]
        pattern = r"(?m)^[1-6]\.\s+(?:" + "|".join(re.escape(title) for title in headings) + r")\s*\n"
        sections = re.split(pattern, raw)
        if len(sections) != 7:
            raise ValueError("Expected six numbered prompt sections")
        contents = [section.strip() for section in sections[1:]]
        contents[0] = contents[0].split("\n", 1)[1].strip()
    async with SessionFactory() as session, session.begin():
        for index, item in enumerate(public):
            category_slug = CATEGORY_SLUGS[index]
            await session.execute(insert(Category).values(slug=category_slug,name=item["category"]).on_conflict_do_nothing(index_elements=[Category.slug]))
            category_id = await session.scalar(select(Category.id).where(Category.slug == category_slug))
            values = {key:value for key,value in item.items() if key != "category"}
            await session.execute(insert(Prompt).values(**values,category_id=category_id,status="published").on_conflict_do_nothing(index_elements=[Prompt.id]))
            if contents:
                await session.execute(insert(PromptVersion).values(prompt_id=item["id"],version=1,content=contents[index]).on_conflict_do_nothing(index_elements=[PromptVersion.prompt_id,PromptVersion.version]))
    await engine.dispose()
    print("Catalog seeded. Protected content is not printed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-file",type=Path)
    args = parser.parse_args()
    asyncio.run(seed(args.content_file))
