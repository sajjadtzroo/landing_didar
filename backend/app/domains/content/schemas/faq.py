import uuid

from pydantic import BaseModel, ConfigDict, Field


class FAQBase(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    is_active: bool = True
    sort_order: int = 0


class FAQCreate(FAQBase):
    pass


class FAQUpdate(BaseModel):
    question: str | None = Field(default=None, min_length=1)
    answer: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None
    sort_order: int | None = None


class FAQOut(FAQBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
