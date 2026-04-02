from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import GoogleLoginRequest, TokenResponse, UserResponse
from app.services.auth_service import get_or_create_user, verify_google_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/google", response_model=TokenResponse)
async def google_login(body: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        idinfo = verify_google_token(body.token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 Google 토큰입니다.",
        )

    google_id = idinfo["sub"]
    email = idinfo["email"]

    user = await get_or_create_user(db, google_id=google_id, email=email)
    access_token = create_access_token(str(user.user_id))

    return TokenResponse(access_token=access_token, user_id=user.user_id)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
