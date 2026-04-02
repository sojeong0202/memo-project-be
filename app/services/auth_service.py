import uuid

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User

# Google 공개키 캐싱을 위한 Request 객체 재사용
_google_request = google_requests.Request()


def verify_google_token(token: str) -> dict:
    """Google id_token을 검증하고 payload를 반환한다."""
    idinfo = id_token.verify_oauth2_token(
        token,
        _google_request,
        settings.google_client_id,
    )
    return idinfo


async def get_or_create_user(db: AsyncSession, google_id: str, email: str) -> User:
    """google_id로 기존 유저를 조회하거나 신규 생성한다."""
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(user_id=uuid.uuid4(), google_id=google_id, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
