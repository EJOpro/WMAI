"""
벡터DB에 테스트용 확정 사례 데이터 추가 스크립트
"""

import sys
import os
from datetime import datetime

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from chrun_backend.rag_pipeline.embedding_service import get_embedding
from chrun_backend.rag_pipeline.vector_db import get_client, upsert_confirmed_chunk

# 테스트 데이터: 다양한 시나리오
test_cases = [
    # ===== 음식점/브랜드 리뷰 (위험 아님) =====
    {
        "sentence": "도미노 피자가 훨씬 나은듯??",
        "confirmed": False,  # 위험 아님
        "risk_score": 0.15,
        "category": "음식점 리뷰"
    },
    {
        "sentence": "이재모 피자 맛없음 ㅋㅋ",
        "confirmed": False,
        "risk_score": 0.18,
        "category": "음식점 리뷰"
    },
    {
        "sentence": "맥도날드 버거가 더 나은 것 같아요",
        "confirmed": False,
        "risk_score": 0.20,
        "category": "음식점 리뷰"
    },
    {
        "sentence": "스타벅스보다 투썸이 낫네",
        "confirmed": False,
        "risk_score": 0.17,
        "category": "음식점 리뷰"
    },
    {
        "sentence": "치킨은 역시 교촌이 최고",
        "confirmed": False,
        "risk_score": 0.12,
        "category": "음식점 리뷰"
    },
    
    # ===== 제품 비교 (위험 아님) =====
    {
        "sentence": "아이폰이 갤럭시보다 나은듯",
        "confirmed": False,
        "risk_score": 0.16,
        "category": "제품 비교"
    },
    {
        "sentence": "맥북 너무 비싼데 윈도우가 낫지 않나요",
        "confirmed": False,
        "risk_score": 0.19,
        "category": "제품 비교"
    },
    
    # ===== 일반적 불만 (위험 아님) =====
    {
        "sentence": "요즘 날씨 너무 추워서 힘들어요",
        "confirmed": False,
        "risk_score": 0.22,
        "category": "일반 불만"
    },
    {
        "sentence": "회사 일이 너무 많아서 그만두고 싶다",
        "confirmed": False,
        "risk_score": 0.35,
        "category": "일반 불만"
    },
    {
        "sentence": "공부하기 싫어서 학교 그만둘까 봐",
        "confirmed": False,
        "risk_score": 0.38,
        "category": "일반 불만"
    },
    
    # ===== 애매한 표현 (위험 아님으로 판정) =====
    {
        "sentence": "다른 곳 알아보는 중이에요",
        "confirmed": False,
        "risk_score": 0.42,
        "category": "애매한 표현"
    },
    {
        "sentence": "이제 정말 그만둘 때가 됐나 봐",
        "confirmed": False,
        "risk_score": 0.40,
        "category": "애매한 표현"
    },
    
    # ===== 서비스 불만 (중간 - 위험 아님) =====
    {
        "sentence": "운영자 맘대로 판단하더니 정지 먹였어요",
        "confirmed": False,
        "risk_score": 0.45,
        "category": "서비스 불만"
    },
    {
        "sentence": "이 기능 좀 개선해주세요 너무 불편해요",
        "confirmed": False,
        "risk_score": 0.35,
        "category": "서비스 불만"
    },
    {
        "sentence": "답답하네요 관리자 응답이 너무 느려요",
        "confirmed": False,
        "risk_score": 0.38,
        "category": "서비스 불만"
    },
    
    # ===== 실제 이탈 위험 (위험 맞음) =====
    {
        "sentence": "여기 있어봐자 소용없을듯요",
        "confirmed": True,  # 위험 맞음!
        "risk_score": 0.85,
        "category": "실제 이탈"
    },
    {
        "sentence": "이 서비스 탈퇴하고 다른 곳으로 갈아탈게요",
        "confirmed": True,
        "risk_score": 0.92,
        "category": "실제 이탈"
    },
    {
        "sentence": "여기 더 있어야 할 이유가 없다고 생각해요",
        "confirmed": True,
        "risk_score": 0.88,
        "category": "실제 이탈"
    },
    {
        "sentence": "계정 삭제하려고 하는데 어디서 하나요",
        "confirmed": True,
        "risk_score": 0.90,
        "category": "실제 이탈"
    },
    {
        "sentence": "이 커뮤니티 떠날 준비 중입니다",
        "confirmed": True,
        "risk_score": 0.87,
        "category": "실제 이탈"
    },
    {
        "sentence": "다른 플랫폼으로 옮길까 봐요 여기는 한계네요",
        "confirmed": True,
        "risk_score": 0.84,
        "category": "실제 이탈"
    },
    {
        "sentence": "더 이상 의미가 없는 것 같아요 탈퇴 고민 중",
        "confirmed": True,
        "risk_score": 0.89,
        "category": "실제 이탈"
    },
    {
        "sentence": "이 사이트 그만 쓸거에요 실망했습니다",
        "confirmed": True,
        "risk_score": 0.86,
        "category": "실제 이탈"
    },
    
    # ===== 경계선 케이스 (문맥 의존적) =====
    {
        "sentence": "이제 바이바이임",
        "confirmed": False,  # 문맥 없이는 위험 아님
        "risk_score": 0.35,
        "category": "경계선"
    },
    {
        "sentence": "정말 마지막이에요",
        "confirmed": False,
        "risk_score": 0.38,
        "category": "경계선"
    },
    {
        "sentence": "더 이상은 못하겠어요",
        "confirmed": False,
        "risk_score": 0.48,
        "category": "경계선"
    },
    
    # ===== 긍정적 표현 (위험 아님) =====
    {
        "sentence": "여기 정말 좋네요 계속 이용할게요",
        "confirmed": False,
        "risk_score": 0.05,
        "category": "긍정"
    },
    {
        "sentence": "이 커뮤니티 최고입니다 감사해요",
        "confirmed": False,
        "risk_score": 0.03,
        "category": "긍정"
    },
]


def populate_vector_db():
    """벡터DB에 테스트 데이터 삽입"""
    
    print("=" * 60)
    print("벡터DB 테스트 데이터 삽입 시작")
    print("=" * 60)
    
    # ChromaDB 클라이언트 생성 (절대 경로 사용)
    try:
        import chromadb
        from chromadb.config import Settings
        
        # 절대 경로로 chroma_store 디렉토리 지정
        persist_dir = os.path.abspath("./chroma_store")
        print(f"\n[INFO] ChromaDB 저장 경로: {persist_dir}")
        
        os.makedirs(persist_dir, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        print("[INFO] ChromaDB 클라이언트 생성 성공!")
        
    except Exception as e:
        print(f"[ERROR] ChromaDB 클라이언트 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n[INFO] 총 {len(test_cases)}개의 테스트 케이스를 삽입합니다.\n")
    
    success_count = 0
    fail_count = 0
    
    for i, case in enumerate(test_cases, 1):
        try:
            sentence = case["sentence"]
            confirmed = case["confirmed"]
            risk_score = case["risk_score"]
            category = case["category"]
            
            print(f"[{i}/{len(test_cases)}] 처리 중: \"{sentence[:40]}...\"")
            print(f"  카테고리: {category}")
            print(f"  판정: {'✅ 위험 맞음' if confirmed else '❌ 위험 아님'} (위험도: {risk_score:.2f})")
            
            # 임베딩 생성
            embedding = get_embedding(sentence)
            
            # 메타데이터 구성
            metadata = {
                "chunk_id": f"test_{i}_{datetime.now().timestamp()}",
                "user_id": f"test_user_{i % 5}",  # 5명의 테스트 유저
                "post_id": f"test_post_{i}",
                "sentence": sentence,
                "risk_score": risk_score,
                "confirmed": confirmed,
                "category": category,
                "created_at": datetime.now().isoformat(),
                "who_labeled": "admin_test",
                "test_data": True  # 테스트 데이터 표시
            }
            
            # 벡터DB에 삽입
            upsert_confirmed_chunk(
                client=client,
                embedding=embedding,
                meta=metadata,
                collection_name="confirmed_risk"
            )
            
            success_count += 1
            print(f"  ✅ 성공!\n")
            
        except Exception as e:
            fail_count += 1
            print(f"  ❌ 실패: {e}\n")
    
    print("=" * 60)
    print(f"삽입 완료!")
    print(f"  성공: {success_count}개")
    print(f"  실패: {fail_count}개")
    print("=" * 60)
    
    # 통계 출력
    try:
        from chrun_backend.rag_pipeline.vector_db import get_collection_stats
        stats = get_collection_stats(client, "confirmed_risk")
        print(f"\n[INFO] 벡터DB 통계:")
        print(f"  총 문서 수: {stats.get('total_documents', 0)}개")
    except Exception as e:
        print(f"\n[WARN] 통계 조회 실패: {e}")


if __name__ == "__main__":
    populate_vector_db()

