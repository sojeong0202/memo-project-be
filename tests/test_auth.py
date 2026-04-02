from unittest.mock import patch

import pytest


async def test_google_login_success(client, test_user):
    """유효한 Google 토큰으로 JWT가 발급된다."""
    mock_idinfo = {"sub": "google_sub_123", "email": "newuser@example.com"}

    with patch("app.services.auth_service.id_token.verify_oauth2_token", return_value=mock_idinfo):
        response = await client.post("/api/auth/google", json={"token": "fake-google-token"})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_google_login_invalid_token(client):
    """잘못된 Google 토큰은 401을 반환한다."""
    with patch("app.services.auth_service.id_token.verify_oauth2_token", side_effect=ValueError("invalid")):
        response = await client.post("/api/auth/google", json={"token": "invalid-token"})

    assert response.status_code == 401


async def test_get_me_success(client, test_user, auth_headers):
    """유효한 JWT로 현재 유저 정보를 조회한다."""
    response = await client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email


async def test_get_me_unauthorized(client):
    """토큰 없이 /me 요청 시 403을 반환한다."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 403


async def test_get_me_invalid_token(client):
    """잘못된 JWT로 /me 요청 시 401을 반환한다."""
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401
