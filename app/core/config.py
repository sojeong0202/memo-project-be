from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str

    # OpenAI
    openai_api_key: str

    # Google OAuth
    google_client_id: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days

    # AI thresholds
    edge_threshold: float = 0.8
    duplicate_threshold: float = 0.95


settings = Settings()
