"""
자동 RAG 분석 결과 샘플 시드 스크립트

mysql/chroma 환경에서 /admin/rag-auto 페이지가 비어있을 경우,
이 스크립트를 실행하면 테스트용 분석 결과를 생성합니다.
"""

from datetime import datetime, timedelta, timezone

from .models import AnalysisRequest
from .service import analyze_and_store


SAMPLE_TEXTS = [
    (
        "user_demo_001",
        "post_demo_001",
        "post",
        "최근 서비스가 너무 별로라서 탈퇴를 심각하게 고민 중입니다. 지원도 느리고 화가 납니다.",
    ),
    (
        "user_demo_002",
        "post_demo_002",
        "comment",
        "이 글만 보고도 마음이 완전히 떠난 느낌이에요. 다른 커뮤니티로 갈아탈 생각입니다.",
    ),
    (
        "user_demo_003",
        "post_demo_003",
        "post",
        "솔직히 많이 아쉽긴 하지만 아직은 지켜보려고요. 그래도 개선이 필요합니다.",
    ),
]


def seed():
    base_time = datetime.now(timezone.utc)
    for idx, (user_id, post_id, post_type, text) in enumerate(SAMPLE_TEXTS):
        created_at = (base_time - timedelta(minutes=idx * 5)).isoformat()
        request = AnalysisRequest(
            user_id=user_id,
            post_id=post_id,
            post_type=post_type,
            text=text,
            created_at=created_at,
            metadata={"seed": True},
        )
        result = analyze_and_store(request)
        print(
            f"[SEED] Analysis stored: id={result['id']} "
            f"user={user_id} post={post_id}"
        )


if __name__ == "__main__":
    seed()

