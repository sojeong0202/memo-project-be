from unittest.mock import AsyncMock, patch

import pytest

MOCK_SUMMARY = "테스트 요약입니다."
MOCK_KEYWORDS = ["테스트", "키워드"]
MOCK_EMBEDDING = [0.1] * 1536


def mock_ai_patches():
    return [
        patch("app.routers.nodes.analyze_text", new=AsyncMock(return_value=(MOCK_SUMMARY, MOCK_KEYWORDS))),
        patch("app.routers.nodes.get_embedding", new=AsyncMock(return_value=MOCK_EMBEDDING)),
    ]


async def test_create_node_success(client, auth_headers):
    """메모 생성 시 요약/키워드/색상이 자동 생성된다."""
    with mock_ai_patches()[0], mock_ai_patches()[1]:
        response = await client.post(
            "/api/nodes",
            json={"text": "테스트 메모입니다"},
            headers=auth_headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["node"]["summary"] == MOCK_SUMMARY
    assert data["node"]["keywords"] == MOCK_KEYWORDS
    assert data["node"]["category_color"] is not None
    assert "new_edges" in data


async def test_create_node_unauthorized(client):
    """인증 없이 노드 생성 시 403을 반환한다."""
    response = await client.post("/api/nodes", json={"text": "테스트"})
    assert response.status_code == 403


async def test_get_node_success(client, auth_headers):
    """생성한 노드를 ID로 조회한다."""
    with mock_ai_patches()[0], mock_ai_patches()[1]:
        create_res = await client.post(
            "/api/nodes",
            json={"text": "조회 테스트 메모"},
            headers=auth_headers,
        )
    node_id = create_res.json()["node"]["node_id"]

    response = await client.get(f"/api/nodes/{node_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["node_id"] == node_id


async def test_get_node_other_user_returns_404(client, auth_headers, other_auth_headers):
    """타인의 노드 조회 시 404를 반환한다."""
    with mock_ai_patches()[0], mock_ai_patches()[1]:
        create_res = await client.post(
            "/api/nodes",
            json={"text": "내 메모"},
            headers=auth_headers,
        )
    node_id = create_res.json()["node"]["node_id"]

    response = await client.get(f"/api/nodes/{node_id}", headers=other_auth_headers)
    assert response.status_code == 404


async def test_patch_node_success(client, auth_headers):
    """노드 요약을 수동으로 수정한다."""
    with mock_ai_patches()[0], mock_ai_patches()[1]:
        create_res = await client.post(
            "/api/nodes",
            json={"text": "수정 테스트 메모"},
            headers=auth_headers,
        )
    node_id = create_res.json()["node"]["node_id"]

    response = await client.patch(
        f"/api/nodes/{node_id}",
        json={"summary": "수동으로 수정한 요약"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["summary"] == "수동으로 수정한 요약"


async def test_delete_node_success(client, auth_headers):
    """노드 삭제 후 조회 시 404를 반환한다."""
    with mock_ai_patches()[0], mock_ai_patches()[1]:
        create_res = await client.post(
            "/api/nodes",
            json={"text": "삭제 테스트 메모"},
            headers=auth_headers,
        )
    node_id = create_res.json()["node"]["node_id"]

    del_res = await client.delete(f"/api/nodes/{node_id}", headers=auth_headers)
    assert del_res.json()["status"] == "success"

    get_res = await client.get(f"/api/nodes/{node_id}", headers=auth_headers)
    assert get_res.status_code == 404
