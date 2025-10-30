"""데이터베이스 연결 및 세션 관리"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import pymysql
from config.settings import settings


# 쓰기 엔진
write_engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

# 읽기 전용 엔진
read_engine = create_engine(
    settings.readonly_database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=False
)

# 세션 팩토리
WriteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=write_engine)
ReadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)


@contextmanager
def get_write_session() -> Generator[Session, None, None]:
    """쓰기 세션 컨텍스트 매니저"""
    session = WriteSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_read_session() -> Generator[Session, None, None]:
    """읽기 세션 컨텍스트 매니저"""
    session = ReadSessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_connection():
    """PyMySQL 연결 생성 (레거시 지원용)"""
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.Cursor
    )


def test_connection() -> bool:
    """데이터베이스 연결 테스트"""
    try:
        with get_write_session() as session:
            session.execute(text("SELECT 1"))
        with get_read_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

