import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.node import Node
from app.models.user import User
from app.schemas.edge import EdgeResponse
from app.schemas.node import NodeCreateRequest, NodePatchRequest, NodeResponse
from app.services.ai_service import analyze_text, get_embedding, keyword_to_color
from app.services.graph_service import process_similarity

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_node(
    body: NodeCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary, keywords = await analyze_text(body.text)
    category_color = keyword_to_color(keywords[0]) if keywords else None
    embedding = await get_embedding(body.text)

    node = Node(
        node_id=uuid.uuid4(),
        user_id=current_user.user_id,
        original_text=body.text,
        summary=summary,
        keywords=keywords,
        embedding=embedding,
        brightness=1,
        category_color=category_color,
    )
    db.add(node)
    await db.flush()

    new_edges = await process_similarity(db, node, embedding)

    return {
        "node": NodeResponse.model_validate(node),
        "new_edges": [EdgeResponse.model_validate(e) for e in new_edges],
    }


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = await _get_node_or_404(db, node_id, current_user.user_id)
    return node


@router.patch("/{node_id}", response_model=NodeResponse)
async def patch_node(
    node_id: uuid.UUID,
    body: NodePatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = await _get_node_or_404(db, node_id, current_user.user_id)

    if body.summary is not None:
        node.summary = body.summary
    if body.keywords is not None:
        node.keywords = body.keywords

    await db.commit()
    await db.refresh(node)
    return node


@router.delete("/{node_id}")
async def delete_node(
    node_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = await _get_node_or_404(db, node_id, current_user.user_id)
    await db.delete(node)
    await db.commit()
    return {"status": "success"}


async def _get_node_or_404(
    db: AsyncSession, node_id: uuid.UUID, user_id: uuid.UUID
) -> Node:
    result = await db.execute(
        select(Node).where(Node.node_id == node_id, Node.user_id == user_id)
    )
    node = result.scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="노드를 찾을 수 없습니다.")
    return node
