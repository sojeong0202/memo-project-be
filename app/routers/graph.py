from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.edge import Edge
from app.models.node import Node
from app.models.user import User
from app.schemas.graph import GraphResponse

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("", response_model=GraphResponse)
async def get_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    nodes_result = await db.execute(
        select(Node).where(Node.user_id == current_user.user_id)
    )
    nodes = nodes_result.scalars().all()

    node_ids = [n.node_id for n in nodes]
    edges_result = await db.execute(
        select(Edge).where(Edge.source_node_id.in_(node_ids))
    )
    edges = edges_result.scalars().all()

    return GraphResponse(nodes=nodes, edges=edges)
