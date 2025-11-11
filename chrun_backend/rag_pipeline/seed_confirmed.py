"""
확정(confirmed) 고위험 문장 시드 스크립트

욕설/강한 부정 문장을 confirmed_risk 컬렉션에 업서트합니다.
"""

from datetime import datetime
from typing import List, Dict

from .vector_db import get_client, get_collection, build_chunk_id, upsert_confirmed_chunk
from .embedding_service import get_embedding, EMBEDDING_DIMENSION


def _load_confirmed_sentences() -> List[Dict[str, str]]:
    """시드용 확정 문장 리스트를 반환합니다."""
    base_time = datetime.utcnow().replace(microsecond=0)
    return [
        {
            "user_id": "rage_user_001",
            "post_id": "rage_post_901",
            "sentence": "이 서비스 진짜 최악이야, 다시는 쓰고 싶지 않아.",
            "risk_score": 0.96,
            "created_at": (base_time.replace(hour=1, minute=5)).isoformat(),
        },
        {
            "user_id": "rage_user_002",
            "post_id": "rage_post_902",
            "sentence": "뭐 하나 제대로 되는 게 없네, 당장 탈퇴하고 싶다.",
            "risk_score": 0.94,
            "created_at": (base_time.replace(hour=1, minute=15)).isoformat(),
        },
        {
            "user_id": "rage_user_003",
            "post_id": "rage_post_903",
            "sentence": "이딴 쓰레기 같은 서비스는 당장 접어야지.",
            "risk_score": 0.97,
            "created_at": (base_time.replace(hour=1, minute=25)).isoformat(),
        },
        {
            "user_id": "rage_user_004",
            "post_id": "rage_post_904",
            "sentence": "고객을 이렇게 무시하는 곳은 처음이야, 꺼져버렸으면.",
            "risk_score": 0.95,
            "created_at": (base_time.replace(hour=1, minute=35)).isoformat(),
        },
        {
            "user_id": "rage_user_005",
            "post_id": "rage_post_905",
            "sentence": "매번 오류만 나고 피가 거꾸로 솟네, 미치겠다 정말.",
            "risk_score": 0.92,
            "created_at": (base_time.replace(hour=1, minute=45)).isoformat(),
        },
        {
            "user_id": "rage_user_006",
            "post_id": "rage_post_906",
            "sentence": "여긴 진짜 지옥이다, 사람 혈압 오르게 만드는 곳.",
            "risk_score": 0.9,
            "created_at": (base_time.replace(hour=1, minute=55)).isoformat(),
        },
        {
            "user_id": "rage_user_007",
            "post_id": "rage_post_907",
            "sentence": "고객센터도 답 없고 진짜 환장하겠다, 다신 안 쓴다.",
            "risk_score": 0.91,
            "created_at": (base_time.replace(hour=2, minute=5)).isoformat(),
        },
        {
            "user_id": "rage_user_008",
            "post_id": "rage_post_908",
            "sentence": "돈값도 못 하는 쓰레기 서비스, 진짜 열받네.",
            "risk_score": 0.93,
            "created_at": (base_time.replace(hour=2, minute=15)).isoformat(),
        },
    ]


def seed_confirmed_sentences(collection_name: str = "confirmed_risk") -> None:
    """
    confirmed_risk 컬렉션에 시드 데이터를 업서트합니다.

    Args:
        collection_name (str): 시드할 컬렉션 이름
    """
    client = get_client()
    collection = get_collection(client, name=collection_name)

    confirmed_sentences = _load_confirmed_sentences()

    inserted = 0
    skipped = 0

    for item in confirmed_sentences:
        chunk_id = build_chunk_id(item["sentence"], item["post_id"])
        metadata = {
            "chunk_id": chunk_id,
            "user_id": item["user_id"],
            "post_id": item["post_id"],
            "sentence": item["sentence"],
            "risk_score": item["risk_score"],
            "created_at": item["created_at"],
            "confirmed": True,
        }

        try:
            existing = collection.get(ids=[chunk_id])
            if existing.get("ids") and existing["ids"][0]:
                skipped += 1
                print(f"[SKIP] 이미 존재하는 chunk_id: {chunk_id}")
                continue
        except Exception as error:
            print(f"[WARN] 기존 데이터 조회 실패({chunk_id}): {error}")

        try:
            embedding = get_embedding(item["sentence"])
        except Exception as error:
            print(f"[WARN] 임베딩 생성 실패({chunk_id}): {error}. 더미 임베딩으로 대체합니다.")
            embedding = [0.0] * EMBEDDING_DIMENSION

        upsert_confirmed_chunk(client, embedding, metadata, collection_name=collection_name)
        inserted += 1
        print(f"[INSERT] 확정 문장 업서트 완료: {chunk_id}")

    final_collection = get_collection(client, name=collection_name)
    total_count = final_collection.count()
    print(f"seed_confirmed inserted={inserted} skipped={skipped} total={total_count}")


if __name__ == "__main__":
    seed_confirmed_sentences()

