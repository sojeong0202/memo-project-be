from unittest.mock import AsyncMock, patch

import pytest

MOCK_EMBEDDING = [0.1] * 1536


async def test_get_graph_empty(client, auth_headers):
    """노드가 없을 때 빈 그래프를 반환한다."""
    response = await client.get("/api/graph", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data


async def test_get_graph_contains_only_own_nodes(client, auth_headers, other_auth_headers):
    """그래프 조회 시 본인 노드만 반환된다."""
    with patch("app.routers.nodes.analyze_text", new=AsyncMock(return_value=("요약", ["키워드"]))), \
         patch("app.routers.nodes.get_embedding", new=AsyncMock(return_value=MOCK_EMBEDDING)):
        await client.post("/api/nodes", json={"text": "내 메모"}, headers=auth_headers)
        await client.post("/api/nodes", json={"text": "타인 메모"}, headers=other_auth_headers)

    my_graph = await client.get("/api/graph", headers=auth_headers)
    my_nodes = my_graph.json()["nodes"]

    assert len(my_nodes) >= 1
    assert all(n["original_text"] != "타인 메모" for n in my_nodes)


async def test_get_graph_unauthorized(client):
    """인증 없이 그래프 조회 시 403을 반환한다."""
    response = await client.get("/api/graph")
    assert response.status_code == 403
