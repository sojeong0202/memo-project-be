import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User


def _make_test_session_factory():
    """NullPool 엔진으로 테스트 세션 팩토리를 생성한다. 이벤트 루프 충돌 방지."""
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def client():
    """매 테스트마다 NullPool get_db로 의존성을 오버라이드한 클라이언트를 제공한다."""
    TestSessionFactory = _make_test_session_factory()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionFactory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(client):
    """테스트용 유저를 DB에 직접 생성한다."""
    TestSessionFactory = _make_test_session_factory()
    user = User(
        user_id=uuid.uuid4(),
        google_id=f"test_google_{uuid.uuid4().hex}",
        email=f"test_{uuid.uuid4().hex}@example.com",
    )
    async with TestSessionFactory() as db:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@pytest.fixture
async def other_user(client):
    """타인 유저 픽스처."""
    TestSessionFactory = _make_test_session_factory()
    user = User(
        user_id=uuid.uuid4(),
        google_id=f"other_google_{uuid.uuid4().hex}",
        email=f"other_{uuid.uuid4().hex}@example.com",
    )
    async with TestSessionFactory() as db:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(str(test_user.user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token(str(other_user.user_id))
    return {"Authorization": f"Bearer {token}"}
