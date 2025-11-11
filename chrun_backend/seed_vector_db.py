"""
ChromaDB에 더미 위험 문장 데이터를 시드하는 스크립트
다양한 위험도 패턴의 실제 커뮤니티 문장들을 저장합니다.
"""

import hashlib
from datetime import datetime, timedelta
import random

from rag_pipeline.vector_db import get_client, upsert_confirmed_chunk
from rag_pipeline.embedding_service import get_embedding


# 🎯 더미 데이터: 위험도별 실제 커뮤니티 문장들
SAMPLE_RISK_SENTENCES = [
    # 🟢 저위험 (0.1 - 0.25): 긍정적, 소속감 강함
    {
        "sentence": "이 커뮤니티 정말 좋아요! 우리 모두 친절해서 기분이 좋네요.",
        "risk_score": 0.12,
        "churn_stage": "1단계: 활발 참여",
        "belongingness": "강함",
        "emotion": "만족"
    },
    {
        "sentence": "재밌는 글들이 많아서 매일 들어와요. 여기 분위기가 최고예요!",
        "risk_score": 0.15,
        "churn_stage": "1단계: 활발 참여",
        "belongingness": "강함",
        "emotion": "만족"
    },
    {
        "sentence": "오늘도 좋은 정보 얻어갑니다. 감사합니다!",
        "risk_score": 0.18,
        "churn_stage": "1단계: 활발 참여",
        "belongingness": "보통",
        "emotion": "만족"
    },
    
    # 🟡 중저위험 (0.25 - 0.4): 소극적, 무관심
    {
        "sentence": "요즘은 그냥 가끔 들어와서 보기만 해요.",
        "risk_score": 0.28,
        "churn_stage": "2단계: 소극 참여",
        "belongingness": "보통",
        "emotion": "무관심"
    },
    {
        "sentence": "뭐 그냥저냥 볼만한 글들이 있긴 하네요.",
        "risk_score": 0.32,
        "churn_stage": "2단계: 소극 참여",
        "belongingness": "약함",
        "emotion": "무관심"
    },
    {
        "sentence": "예전만큼은 아니지만 가끔 들어와요.",
        "risk_score": 0.35,
        "churn_stage": "2단계: 소극 참여",
        "belongingness": "보통",
        "emotion": "무관심"
    },
    
    # 🟠 중위험 (0.4 - 0.6): 관계 단절, 실망 ⚠️ 골든타임!
    {
        "sentence": "검색 정확도가 좀만 더 좋으면… 관련 없는 글이 자꾸 섞여요.",
        "risk_score": 0.42,
        "churn_stage": "3단계: 관계 단절",
        "belongingness": "약함",
        "emotion": "실망"
    },
    {
        "sentence": "개선되면 계속 볼 의향 있습니다.",
        "risk_score": 0.45,
        "churn_stage": "3단계: 관계 단절",
        "belongingness": "보통",
        "emotion": "실망"
    },
    {
        "sentence": "광고 빈도만 줄여주면 계속 쓸게요. 광고가 과해서 집중이 안 돼요.",
        "risk_score": 0.48,
        "churn_stage": "3단계: 관계 단절",
        "belongingness": "약함",
        "emotion": "짜증"
    },
    {
        "sentence": "요즘 여기 사람들 별로네요. 소통이 안 되는 느낌이에요.",
        "risk_score": 0.52,
        "churn_stage": "3단계: 관계 단절",
        "belongingness": "약함",
        "emotion": "실망"
    },
    {
        "sentence": "예전같지 않네요. 혼자 있는 것 같아요.",
        "risk_score": 0.55,
        "churn_stage": "3단계: 관계 단절",
        "belongingness": "약함",
        "emotion": "실망"
    },
    {
        "sentence": "콘텐츠 품질이 많이 떨어진 것 같아요. 아쉽네요.",
        "risk_score": 0.58,
        "churn_stage": "3단계: 관계 단절",
        "belongingness": "보통",
        "emotion": "실망"
    },
    
    # 🔴 고위험 (0.6 - 0.85): 대안 탐색
    {
        "sentence": "다른 커뮤니티도 알아보고 있어요. XX 커뮤니티가 괜찮더라고요.",
        "risk_score": 0.65,
        "churn_stage": "4단계: 대안 탐색",
        "belongingness": "약함",
        "emotion": "무관심"
    },
    {
        "sentence": "여기가 아니어도 활동할 곳은 많습니다. 다른 곳 알아보는 중이에요.",
        "risk_score": 0.70,
        "churn_stage": "4단계: 대안 탐색",
        "belongingness": "없음",
        "emotion": "포기"
    },
    {
        "sentence": "XX 서비스가 여기보다 훨씬 좋던데요. 갈아탈까 고민 중입니다.",
        "risk_score": 0.75,
        "churn_stage": "4단계: 대안 탐색",
        "belongingness": "없음",
        "emotion": "무관심"
    },
    {
        "sentence": "다른 곳에 가입했어요. 거기가 더 활발하네요.",
        "risk_score": 0.78,
        "churn_stage": "4단계: 대안 탐색",
        "belongingness": "없음",
        "emotion": "포기"
    },
    {
        "sentence": "이제 더 이상 여기 있을 이유가 없는 것 같아요.",
        "risk_score": 0.82,
        "churn_stage": "4단계: 대안 탐색",
        "belongingness": "없음",
        "emotion": "포기"
    },
    
    # ⚫ 최고위험 (0.85 - 1.0): 작별
    {
        "sentence": "그동안 감사했습니다. 탈퇴할게요.",
        "risk_score": 0.88,
        "churn_stage": "5단계: 작별",
        "belongingness": "없음",
        "emotion": "포기"
    },
    {
        "sentence": "마지막 글 남기고 갑니다. 안녕히 계세요.",
        "risk_score": 0.90,
        "churn_stage": "5단계: 작별",
        "belongingness": "없음",
        "emotion": "포기"
    },
    {
        "sentence": "탈퇴 신청했어요. 더 이상 사용하지 않을 예정입니다.",
        "risk_score": 0.92,
        "churn_stage": "5단계: 작별",
        "belongingness": "없음",
        "emotion": "포기"
    },
    {
        "sentence": "여기는 이제 의미가 없네요. 완전히 떠날 겁니다.",
        "risk_score": 0.95,
        "churn_stage": "5단계: 작별",
        "belongingness": "없음",
        "emotion": "포기"
    },
]


def generate_chunk_id(sentence: str, user_id: str) -> str:
    """chunk_id 생성 (해시)"""
    content = f"{sentence}_{user_id}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def seed_vector_db():
    """ChromaDB에 더미 데이터를 시드합니다."""
    print("=" * 60)
    print("[SEED] ChromaDB 더미 데이터 시드 시작")
    print("=" * 60)
    
    # ChromaDB 클라이언트 가져오기 (프로젝트 루트 기준 경로)
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chroma_dir = os.path.join(project_root, "chroma_store")
    print(f"[INFO] ChromaDB 경로: {chroma_dir}")
    
    client = get_client(persist_dir=chroma_dir)
    
    if client is None:
        print("[ERROR] ChromaDB 클라이언트를 초기화할 수 없습니다.")
        print("[ERROR] ChromaDB가 설치되어 있는지 확인하세요: pip install chromadb")
        return
    
    # 기준 날짜 (1개월 전부터 시작)
    base_date = datetime.now() - timedelta(days=30)
    
    success_count = 0
    fail_count = 0
    
    for i, sample in enumerate(SAMPLE_RISK_SENTENCES, 1):
        try:
            # 더미 사용자/게시물 ID 생성
            user_id = f"seed_user_{i:03d}"
            post_id = f"seed_post_{i:03d}"
            
            # 시간 간격 (3일 정도씩)
            created_at = (base_date + timedelta(days=i * 3)).isoformat()
            
            # chunk_id 생성
            chunk_id = generate_chunk_id(sample["sentence"], user_id)
            
            print(f"\n[{i}/{len(SAMPLE_RISK_SENTENCES)}] 처리 중...")
            print(f"  문장: {sample['sentence'][:50]}...")
            print(f"  위험도: {sample['risk_score']:.2f} ({sample['churn_stage']})")
            
            # 임베딩 생성
            print(f"  임베딩 생성 중... ", end="", flush=True)
            embedding = get_embedding(sample["sentence"])
            print("[OK]")
            
            # 메타데이터 구성
            metadata = {
                "chunk_id": chunk_id,
                "user_id": user_id,
                "post_id": post_id,
                "sentence": sample["sentence"],
                "risk_score": sample["risk_score"],
                "created_at": created_at,
                "confirmed": True,  # 확인된 위험 문장
                
                # 추가 메타데이터
                "churn_stage": sample.get("churn_stage", ""),
                "belongingness": sample.get("belongingness", ""),
                "emotion": sample.get("emotion", ""),
                "embed_model_v": "text-embedding-3-small",
                "embed_dimension": len(embedding),
                "who_labeled": "seed_script",
                "reason": "Initial seed data for RAG system"
            }
            
            # ChromaDB에 저장
            print(f"  ChromaDB 저장 중... ", end="", flush=True)
            upsert_confirmed_chunk(client, embedding, metadata)
            print("[OK]")
            
            success_count += 1
            
        except Exception as e:
            print(f"[ERROR] 실패: {e}")
            fail_count += 1
            continue
    
    print("\n" + "=" * 60)
    print("[COMPLETE] 시드 완료!")
    print("=" * 60)
    print(f"[OK] 성공: {success_count}개")
    print(f"[FAIL] 실패: {fail_count}개")
    print(f"[INFO] 총 {success_count}개의 문장이 VectorDB에 저장되었습니다.")
    print("=" * 60)
    
    # 통계 출력
    from rag_pipeline.vector_db import get_collection_stats
    stats = get_collection_stats(client)
    print(f"\n[STATS] VectorDB 통계:")
    print(f"  - 컬렉션: {stats.get('collection_name')}")
    print(f"  - 총 문서 수: {stats.get('document_count')}")
    print(f"  - 임베딩 차원: {stats.get('embedding_dimension')}")


if __name__ == "__main__":
    import sys
    import os
    
    # 환경 변수 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 설정하고 다시 실행하세요.")
        sys.exit(1)
    
    # 시드 실행
    try:
        seed_vector_db()
    except KeyboardInterrupt:
        print("\n\n[WARNING] 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

