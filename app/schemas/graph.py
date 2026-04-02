from pydantic import BaseModel

from app.schemas.edge import EdgeResponse
from app.schemas.node import NodeResponse


class GraphResponse(BaseModel):
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]
