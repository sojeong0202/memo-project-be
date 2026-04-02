import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.edge import Edge
from app.models.node import Node


async def find_similar_nodes(
    db: AsyncSession,
    user_id: uuid.UUID,
    embedding: list[float],
    limit: int = 20,
) -> list[tuple[Node, float]]:
    """현재 유저의 기존 노드들과 코사인 유사도를 계산하여 상위 N개를 반환한다."""
    result = await db.execute(
        select(
            Node,
            (1 - Node.embedding.cosine_distance(embedding)).label("similarity"),
        )
        .where(Node.user_id == user_id)
        .where(Node.embedding.is_not(None))
        .order_by(Node.embedding.cosine_distance(embedding))
        .limit(limit)
    )
    return [(row.Node, row.similarity) for row in result.all()]


async def process_similarity(
    db: AsyncSession,
    new_node: Node,
    embedding: list[float],
) -> list[Edge]:
    """유사도 기반으로 엣지 생성 또는 중복 노드 업데이트를 처리한다.

    - similarity >= DUPLICATE_THRESHOLD: 기존 노드 updated_at 갱신, brightness +1
    - EDGE_THRESHOLD <= similarity < DUPLICATE_THRESHOLD: 새 Edge 생성
    - similarity < EDGE_THRESHOLD: 아무 처리 없음
    """
    similar_nodes = await find_similar_nodes(db, new_node.user_id, embedding)
    new_edges: list[Edge] = []

    for existing_node, similarity in similar_nodes:
        if existing_node.node_id == new_node.node_id:
            continue

        if similarity >= settings.duplicate_threshold:
            existing_node.updated_at = datetime.now(timezone.utc)
            existing_node.brightness = min(existing_node.brightness + 1, 10)

        elif similarity >= settings.edge_threshold:
            edge = Edge(
                edge_id=uuid.uuid4(),
                source_node_id=new_node.node_id,
                target_node_id=existing_node.node_id,
                similarity_score=float(similarity),
                is_manual=False,
            )
            db.add(edge)
            new_edges.append(edge)

    await db.commit()
    return new_edges
