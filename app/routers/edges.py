import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.edge import Edge
from app.models.node import Node
from app.models.user import User

router = APIRouter(prefix="/api/edges", tags=["edges"])


@router.delete("/{edge_id}")
async def delete_edge(
    edge_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Edge)
        .join(Node, Edge.source_node_id == Node.node_id)
        .where(Edge.edge_id == edge_id, Node.user_id == current_user.user_id)
    )
    edge = result.scalar_one_or_none()

    if edge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="엣지를 찾을 수 없습니다.")

    await db.delete(edge)
    await db.commit()
    return {"status": "success"}
