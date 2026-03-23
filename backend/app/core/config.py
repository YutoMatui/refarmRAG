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
    NOTION_DATABASE_ID: str
    FRONTEND_URL: str = "http://localhost:5173"
    EMBEDDING_DIM: int = 768


settings = Settings()
