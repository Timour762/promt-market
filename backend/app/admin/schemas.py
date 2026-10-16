from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class PromptFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    category_id: int = Field(gt=0)
    description: str = Field(min_length=1, max_length=6000)
    result: str = Field(min_length=1, max_length=8000)
    symbol: str = Field(min_length=1, max_length=20)
    price_minor: int | None = Field(default=None, ge=0, le=2147483647, strict=True)
    content: str = Field(default="", max_length=100000)
    @field_validator("title", "description", "result", "symbol", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value

class PromptCreate(PromptFields):
    id: str = Field(min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9-]+$")
    @field_validator("id")
    @classmethod
    def reserved_slug(cls, value):
        if value == "new":
            raise ValueError("Choose a different URL identifier")
        return value

class PromptEdit(PromptFields):
    revision: int = Field(ge=1)

class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
