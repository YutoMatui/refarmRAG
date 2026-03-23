from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    NOTION_API_KEY: str
    NOTION_ROOT_PAGE_ID: str
    NOTION_SYNC_MAX_PAGES: int = 0
    NOTION_SYNC_MAX_RETRIES: int = 5
    NOTION_SYNC_DELAY_SECONDS: float = 0.0
    NOTION_SYNC_MAX_BLOCKS_PER_PAGE: int = 0
    FRONTEND_URL: str = "http://localhost:5173"
    EMBEDDING_DIM: int = 768


settings = Settings()
