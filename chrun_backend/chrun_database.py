from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from urllib.parse import quote_plus

# 환경 변수에서 데이터베이스 설정 읽기
# 기본적으로 SQLite 사용 (개발 환경)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./churn_analysis.db"
)

# MySQL 연결 설정
# 기존 팀 프로젝트 환경 변수 우선 사용 (DB_*), 없으면 CHURN_MYSQL_*, 없으면 기본값
# 환경 변수 우선순위:
# 1. DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT (기존 팀 설정)
# 2. CHURN_MYSQL_HOST, CHURN_MYSQL_USER, CHURN_MYSQL_PASSWORD, CHURN_MYSQL_DATABASE, CHURN_MYSQL_PORT
# 3. 기본값 (localhost:3306, wmai/wmai_db)

# MySQL 사용 여부 확인
# 1. USE_MYSQL 환경 변수가 명시적으로 설정되어 있으면 그 값 사용
# 2. 기존 팀 DB 설정(DB_HOST 등)이 있으면 자동으로 MySQL 사용
# 3. ENVIRONMENT가 production이면 MySQL 사용
USE_MYSQL = os.getenv("USE_MYSQL", "").lower() == "true"
if not USE_MYSQL:
    # 기존 팀 DB 설정이 있으면 자동으로 MySQL 사용
    has_team_db_config = bool(os.getenv("DB_HOST") or os.getenv("DB_USER") or os.getenv("DB_NAME"))
    USE_MYSQL = has_team_db_config or os.getenv("ENVIRONMENT") == "production"

if USE_MYSQL:
    # 기존 팀 프로젝트 환경 변수 우선 사용 (DB_*)
    # 없으면 CHURN_MYSQL_* 사용, 없으면 기본값
    mysql_host = os.getenv("DB_HOST") or os.getenv("CHURN_MYSQL_HOST", "localhost")
    mysql_port = os.getenv("DB_PORT") or os.getenv("CHURN_MYSQL_PORT", "3306")
    mysql_user = os.getenv("DB_USER") or os.getenv("CHURN_MYSQL_USER", "wmai")
    mysql_password = os.getenv("DB_PASSWORD") or os.getenv("CHURN_MYSQL_PASSWORD", "1234")
    mysql_database = os.getenv("DB_NAME") or os.getenv("CHURN_MYSQL_DATABASE", "wmai_db")
    
    # 비밀번호 URL 인코딩 (특수문자 처리)
    if mysql_password:
        mysql_password = quote_plus(mysql_password)
    
    # MySQL 연결 문자열 생성
    DATABASE_URL = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}"
    
    print(f"[INFO] MySQL 연결 설정: {mysql_user}@{mysql_host}:{mysql_port}/{mysql_database}")

# SQLAlchemy 엔진 생성
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true"
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true"
    )

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()

# 의존성 주입용 DB 세션
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 데이터베이스 초기화
def init_db():
    """데이터베이스 테이블 생성"""
    from .chrun_models import Base
    Base.metadata.create_all(bind=engine)

# 데이터베이스 연결 테스트
def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        with engine.connect() as connection:
            from sqlalchemy import text
            connection.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"데이터베이스 연결 실패: {e}")
        return False
