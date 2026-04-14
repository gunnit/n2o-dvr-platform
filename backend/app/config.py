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
    # SDS PDF extraction — vision + structured outputs
    OPENAI_MODEL_EXTRACTION: str = "gpt-5.4-mini"
    # Short Italian boilerplate (company descriptions)
    OPENAI_MODEL_GENERATION: str = "gpt-5-nano"
    # Domain reasoning for improvement measures
    OPENAI_MODEL_MEASURES: str = "gpt-5-mini"
    # Optional "max quality" toggle for hard cases
    OPENAI_MODEL_PREMIUM: str = "gpt-5.4"
    # Request timeout in seconds (OpenAI default is 10 min, we tighten for UX)
    OPENAI_TIMEOUT_SECONDS: float = 60.0

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
