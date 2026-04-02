import uuid
from datetime import datetime

from pydantic import BaseModel


class EdgeResponse(BaseModel):
    edge_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    similarity_score: float
    is_manual: bool
    created_at: datetime

    model_config = {"from_attributes": True}
