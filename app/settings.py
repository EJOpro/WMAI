import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 기본 설정
    API_BASE: str = os.getenv("API_BASE", "")
    MODE: str = os.getenv("MODE", "development")
    
    # 서버 설정
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

