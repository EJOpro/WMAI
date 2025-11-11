"""애플리케이션 설정"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """환경 변수 기반 설정"""
    
    # MySQL 설정
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "wmai_db"
    MYSQL_USER: str = "wmai"
    MYSQL_PASSWORD: str = "1234"
    READONLY_USER: str = "wmai"
    READONLY_PASSWORD: str = "1234"
    
    # Redis 설정
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    
    # API 인증
    READ_TRENDS_KEY: str = "dev_key_123"
    
    # 타임존
    TZ: str = "UTC"
    
    # 애플리케이션 설정
    API_VERSION: str = "v1"
    CACHE_TTL_SECONDS: int = 120
    AGGREGATION_INTERVAL_SECONDS: int = 60
    
    # 로그 레벨
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def database_url(self) -> str:
        """쓰기 DB URL"""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
    
    @property
    def readonly_database_url(self) -> str:
        """읽기 전용 DB URL"""
        return f"mysql+pymysql://{self.READONLY_USER}:{self.READONLY_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
    
    @property
    def redis_url(self) -> str:
        """Redis URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()

