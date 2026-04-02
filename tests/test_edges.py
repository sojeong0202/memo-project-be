import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.edge import Edge
from app.models.node import Node

MOCK_EMBEDDING = [0.1] * 1536


async def _create_test_node(client, auth_headers, text="테스트 메모"):
    with patch("app.routers.nodes.analyze_text", new=AsyncMock(return_value=("요약", ["키워드"]))), \
         patch("app.routers.nodes.get_embedding", new=AsyncMock(return_value=MOCK_EMBEDDING)):
        res = await client.post("/api/nodes", json={"text": text}, headers=auth_headers)
    return res.json()["node"]["node_id"]


async def _create_edge_directly(source_node_id: str, target_node_id: str) -> str:
    """테스트용 엣지를 DB에 직접 생성한다."""
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    edge = Edge(
        edge_id=uuid.uuid4(),
        source_node_id=uuid.UUID(source_node_id),
        target_node_id=uuid.UUID(target_node_id),
        similarity_score=0.9,
        is_manual=False,
    )
    async with session_factory() as db:
        db.add(edge)
        await db.commit()
        await db.refresh(edge)
    await engine.dispose()
    return str(edge.edge_id)


async def test_delete_edge_success(client, auth_headers):
    """엣지 삭제 후 그래프에서 사라진다."""
    node1_id = await _create_test_node(client, auth_headers, "노드1")
    node2_id = await _create_test_node(client, auth_headers, "노드2")
    edge_id = await _create_edge_directly(node1_id, node2_id)

    response = await client.delete(f"/api/edges/{edge_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"


async def test_delete_edge_other_user_returns_404(client, auth_headers, other_auth_headers):
    """타인의 엣지 삭제 시 404를 반환한다."""
    node1_id = await _create_test_node(client, auth_headers, "내 노드1")
    node2_id = await _create_test_node(client, auth_headers, "내 노드2")
    edge_id = await _create_edge_directly(node1_id, node2_id)

    response = await client.delete(f"/api/edges/{edge_id}", headers=other_auth_headers)
    assert response.status_code == 404


async def test_delete_nonexistent_edge(client, auth_headers):
    """존재하지 않는 엣지 삭제 시 404를 반환한다."""
    response = await client.delete(f"/api/edges/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404
