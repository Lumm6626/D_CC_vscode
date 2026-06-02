from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Login API"
    DATABASE_URL: str = "sqlite+aiosqlite:///./login.db"
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()