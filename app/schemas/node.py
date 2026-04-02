import uuid
from datetime import datetime

from pydantic import BaseModel


class NodeCreateRequest(BaseModel):
    text: str


class NodePatchRequest(BaseModel):
    summary: str | None = None
    keywords: list[str] | None = None


class NodeResponse(BaseModel):
    node_id: uuid.UUID
    original_text: str
    summary: str | None
    keywords: list[str] | None
    brightness: int
    category_color: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
