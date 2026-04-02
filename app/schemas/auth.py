import uuid
from datetime import datetime

from pydantic import BaseModel


class GoogleLoginRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID


class UserResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}
