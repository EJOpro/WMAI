import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _get_database_url() -> str:
    return (
        os.getenv("RISK_DB_URL")
        or os.getenv("DATABASE_URL")
        or "sqlite:///./risk_demo.sqlite3"
    )


@lru_cache(maxsize=1)
def get_engine():
    url = _get_database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, pool_pre_ping=True, future=True, connect_args=connect_args)
    return engine


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def get_session():
    return SessionLocal()

