"""
고위험 문장 및 피드백 저장소 (MySQL/SQLite 겸용)
"""

import hashlib
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    select,
    update,
    func,
    insert,
    desc,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .db_core import get_engine, get_session

metadata = MetaData()

high_risk_chunks = Table(
    "high_risk_chunks",
    metadata,
    Column("chunk_id", String(64), primary_key=True),
    Column("user_id", String(128)),
    Column("post_id", String(128)),
    Column("sentence", String(2048)),
    Column("risk_score", Float),
    Column("created_at", String(64)),
    Column("confirmed", Integer, default=0),
)

feedback_events = Table(
    "feedback_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("chunk_id", String(64)),
    Column("user_hash", String(64)),
    Column("sentence", String(2048)),
    Column("pred_score", Float),
    Column("final_label", String(32)),
    Column("confirmed", Integer),
    Column("created_at", String(64)),
    Column("short_hash", String(32), nullable=True),
)


def _ensure_tables(engine: Engine) -> None:
    metadata.create_all(engine)


def init_db() -> None:
    """
    데이터베이스 초기화 및 샘플 데이터 삽입 (비어 있을 때)
    """
    engine = get_engine()
    _ensure_tables(engine)

    try:
        with get_session() as session:
            count_stmt = select(func.count()).select_from(high_risk_chunks)
            total = session.execute(count_stmt).scalar_one()

            if total == 0:
                sample_data = [
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "user_id": "user_001",
                        "post_id": "post_123",
                        "sentence": "서비스 떠날까 고민 중이에요... 여기 있을 이유가 없어 보여서",
                        "risk_score": 0.91,
                        "created_at": "2025-10-31T14:00:00",
                        "confirmed": 0,
                    },
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "user_id": "user_017",
                        "post_id": "post_456",
                        "sentence": "탈퇴할까 생각중입니다 진짜로 더 이상 의미가 없는 것 같아요",
                        "risk_score": 0.87,
                        "created_at": "2025-10-31T13:45:00",
                        "confirmed": 1,
                    },
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "user_id": "user_042",
                        "post_id": "post_789",
                        "sentence": "여기 더 있어야 할 이유가 없다고 생각해요 떠날 때가 된 것 같습니다",
                        "risk_score": 0.83,
                        "created_at": "2025-10-31T13:30:00",
                        "confirmed": 0,
                    },
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "user_id": "user_088",
                        "post_id": "post_321",
                        "sentence": "이 서비스 그만 쓸까 봐요 다른 곳으로 옮기는 게 나을 것 같아서",
                        "risk_score": 0.79,
                        "created_at": "2025-10-31T13:15:00",
                        "confirmed": 1,
                    },
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "user_id": "user_156",
                        "post_id": "post_654",
                        "sentence": "계정 삭제하고 싶은데 어떻게 하나요? 더 이상 사용할 일이 없을 것 같아요",
                        "risk_score": 0.75,
                        "created_at": "2025-10-31T13:00:00",
                        "confirmed": 0,
                    },
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "user_id": "user_203",
                        "post_id": "post_987",
                        "sentence": "이제 정말 그만둘 때가 된 것 같습니다 다른 대안을 찾아보고 있어요",
                        "risk_score": 0.72,
                        "created_at": "2025-10-31T12:45:00",
                        "confirmed": 1,
                    },
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "user_id": "user_299",
                        "post_id": "post_111",
                        "sentence": "서비스 품질이 너무 떨어져서 이탈을 고려하고 있습니다",
                        "risk_score": 0.68,
                        "created_at": "2025-10-31T12:30:00",
                        "confirmed": 0,
                    },
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "user_id": "user_334",
                        "post_id": "post_222",
                        "sentence": "다른 플랫폼으로 갈아탈까 생각 중입니다 여기는 한계가 있는 것 같아요",
                        "risk_score": 0.65,
                        "created_at": "2025-10-31T12:15:00",
                        "confirmed": 1,
                    },
                ]
                session.execute(insert(high_risk_chunks), sample_data)
                session.commit()
                print(f"[INFO] 샘플 고위험 문장 {len(sample_data)}건 삽입 완료")
    except SQLAlchemyError as exc:
        print(f"[ERROR] DB 초기화 중 오류 발생: {exc}")
        raise


def _row_to_dict(row) -> Dict[str, Any]:
    return dict(row)


def get_recent_high_risk(limit: int = 5, only_unconfirmed: bool = True) -> List[Dict[str, Any]]:
    """
    고위험 문장 조회
    
    Args:
        limit: 최대 조회 개수
        only_unconfirmed: True면 confirmed=0인 항목만, False면 모두 조회
    """
    with get_session() as session:
        stmt = select(high_risk_chunks)
        
        # confirmed=0인 항목만 필터링 (관리자가 아직 처리하지 않은 것들)
        if only_unconfirmed:
            stmt = stmt.where(high_risk_chunks.c.confirmed == 0)
        
        stmt = stmt.order_by(desc(high_risk_chunks.c.created_at)).limit(limit)
        
        rows = session.execute(stmt).mappings().all()
        results = [_row_to_dict(r) for r in rows]
        print(f"[INFO] 고위험 문장 {len(results)}건 조회 (only_unconfirmed={only_unconfirmed})")
        return results


def get_chunk_by_id(chunk_id: str) -> Dict[str, Any]:
    with get_session() as session:
        stmt = select(high_risk_chunks).where(high_risk_chunks.c.chunk_id == chunk_id)
        row = session.execute(stmt).mappings().first()
        if row:
            print(f"[INFO] chunk 조회 완료: {chunk_id}")
            return _row_to_dict(row)
        print(f"[WARN] chunk를 찾을 수 없음: {chunk_id}")
        return {}


def save_high_risk_chunk(chunk_dict: Dict[str, Any]) -> None:
    chunk_id = chunk_dict.get("chunk_id", str(uuid.uuid4()))
    payload = {
        "chunk_id": chunk_id,
        "user_id": chunk_dict.get("user_id", ""),
        "post_id": chunk_dict.get("post_id", ""),
        "sentence": chunk_dict.get("sentence", ""),
        "risk_score": float(chunk_dict.get("risk_score", 0.0)),
        "created_at": chunk_dict.get("created_at", datetime.now().isoformat()),
        "confirmed": 1 if chunk_dict.get("confirmed", 0) else 0,
    }
    with get_session() as session:
        exists_stmt = select(high_risk_chunks.c.chunk_id).where(
            high_risk_chunks.c.chunk_id == chunk_id
        )
        exists = session.execute(exists_stmt).scalar_one_or_none()
        if exists:
            session.execute(
                update(high_risk_chunks)
                .where(high_risk_chunks.c.chunk_id == chunk_id)
                .values(**payload)
            )
        else:
            session.execute(insert(high_risk_chunks).values(**payload))
        session.commit()
    print(f"[INFO] 고위험 문장 저장 완료: {chunk_id}")


def update_feedback(
    chunk_id: str,
    confirmed: bool,
    who_labeled: Optional[str] = None,
    segment: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    with get_session() as session:
        stmt = (
            update(high_risk_chunks)
            .where(high_risk_chunks.c.chunk_id == chunk_id)
            .values(confirmed=1 if confirmed else 0)
        )
        result = session.execute(stmt)
        session.commit()
        if result.rowcount == 0:
            print(f"[WARN] chunk_id를 찾을 수 없음: {chunk_id}")
            return
        print(f"[INFO] 피드백 업데이트 완료: {chunk_id} confirmed={confirmed}")

    if confirmed:
        try:
            chunk_data = get_chunk_by_id(chunk_id)
            if chunk_data:
                from .vector_store import get_vector_store
                from .embedding_service import get_embedding

                vector_store = get_vector_store()
                sentence = chunk_data.get("sentence", "")
                if sentence:
                    embedding = get_embedding(sentence)
                    metadata_dict = {
                        "user_id": chunk_data.get("user_id", ""),
                        "post_id": chunk_data.get("post_id", ""),
                        "sentence": sentence,
                        "risk_score": chunk_data.get("risk_score", 0.0),
                        "created_at": chunk_data.get(
                            "created_at", datetime.now().isoformat()
                        ),
                    }
                    vector_store.upsert_high_risk_chunk(
                        embedding=embedding,
                        metadata_dict=metadata_dict,
                        confirmed=True,
                        who_labeled=who_labeled or "admin",
                        segment=segment,
                        reason=reason,
                    )
                    print(f"[INFO] 벡터DB에 확정 청크 upsert 완료: {chunk_id}")
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] 벡터DB upsert 실패: {exc}")


def log_feedback_event(
    chunk_id: str,
    sentence: str,
    pred_score: float,
    final_label: str,
    confirmed: bool,
    user_id: Optional[str] = None,
) -> int:
    hashed_user = _hash_identifier(user_id)
    created_at = datetime.now().isoformat()
    payload = {
        "chunk_id": chunk_id,
        "user_hash": hashed_user,
        "sentence": sentence[:500],
        "pred_score": float(pred_score),
        "final_label": final_label,
        "confirmed": 1 if confirmed else 0,
        "created_at": created_at,
    }
    with get_session() as session:
        result = session.execute(insert(feedback_events), payload)
        session.commit()
        event_id = result.inserted_primary_key[0]
    return event_id


def get_feedback_events(limit: int = 50) -> List[Dict[str, Any]]:
    with get_session() as session:
        stmt = (
            select(feedback_events)
            .order_by(desc(feedback_events.c.created_at))
            .limit(limit)
        )
        rows = session.execute(stmt).mappings().all()
        return [_row_to_dict(r) for r in rows]


def _hash_identifier(value: Optional[str]) -> str:
    if not value:
        return "anonymous"
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    print("[INFO] 위험 문장 저장소 초기화를 시작합니다.")
    init_db()