from pydantic import BaseModel

class PublicPrompt(BaseModel):
    id: str
    title: str
    category: str
    description: str
    symbol: str
    result: str
    price_minor: int | None
    currency: str
