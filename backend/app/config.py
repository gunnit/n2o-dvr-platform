from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "N2O DVR API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:dev@localhost:5432/n2o"

    # Auth
    AUTH_SECRET: str = "change-me-in-production"
    AUTH_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_EXTRACTION: str = "gpt-4.1"
    OPENAI_MODEL_GENERATION: str = "gpt-4.1-mini"

    # Google Drive
    GOOGLE_DRIVE_FOLDER_ID: str = "13aHCy8D78JwJzgffxYbqe7Nmyed84may"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # File storage
    FILE_STORAGE_PATH: str = "/data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
