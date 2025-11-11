from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy import Table, Column, Integer, String, Float, DateTime, JSON, MetaData, select, insert, desc

from .db_core import get_engine, get_session

metadata = MetaData()

analysis_results = Table(
    "analysis_results",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", String(128)),
    Column("post_id", String(128)),
    Column("post_type", String(32)),
    Column("risk_score", Float),
    Column("priority", String(16)),
    Column("decision", JSON),
    Column("evidence", JSON),
    Column("created_at", DateTime, default=datetime.utcnow),
)


def init_repository():
    engine = get_engine()
    metadata.create_all(engine)


def save_analysis_result(result: Dict[str, Any]) -> int:
    with get_session() as session:
        stmt = insert(analysis_results).values(**result)
        res = session.execute(stmt)
        session.commit()
        return res.inserted_primary_key[0]


def get_recent_results(limit: int = 50) -> List[Dict[str, Any]]:
    with get_session() as session:
        stmt = (
            select(analysis_results)
            .order_by(desc(analysis_results.c.created_at))
            .limit(limit)
        )
        rows = session.execute(stmt).mappings().all()
        return [dict(row) for row in rows]


# 초기화
init_repository()

