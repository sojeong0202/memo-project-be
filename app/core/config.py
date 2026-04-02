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
    jwt_algorithm: str
    jwt_expire_minutes: int

    # AI thresholds
    edge_threshold: float
    duplicate_threshold: float


settings = Settings()
