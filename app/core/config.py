from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Railway는 postgresql:// 형식으로 제공하므로 asyncpg 드라이버 형식으로 변환한다."""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # OpenAI
    openai_api_key: str

    # Google OAuth
    google_client_id: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expire_minutes: int

    # AI thresholds
    edge_threshold: float
    duplicate_threshold: float


settings = Settings()
