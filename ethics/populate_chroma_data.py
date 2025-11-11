"""
ChromaDB에 다양한 비윤리/스팸 케이스 데이터를 추가하는 스크립트
실제 사용 시나리오를 반영한 샘플 데이터를 생성합니다.
"""

import sys
import os
from datetime import datetime, timedelta
import random

# PYTHONPATH 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_sample_cases():
    """다양한 비윤리/스팸 케이스 샘플 데이터 생성"""
    
    # 비윤리 케이스들
    immoral_cases = [
        {
            "sentence": "너 진짜 죽고 싶냐? 집 주소 알려줘",
            "immoral_score": 95.0,
            "spam_score": 20.0,
            "confidence": 92.0,
            "types": ["threat", "violence"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "여자들은 다 바보야, 남자가 더 우월해",
            "immoral_score": 88.0,
            "spam_score": 15.0,
            "confidence": 85.0,
            "types": ["discrimination", "sexism"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "흑인들은 모두 범죄자다",
            "immoral_score": 92.0,
            "spam_score": 10.0,
            "confidence": 90.0,
            "types": ["racism", "discrimination"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "장애인은 사회에 도움이 안 된다",
            "immoral_score": 89.0,
            "spam_score": 12.0,
            "confidence": 87.0,
            "types": ["discrimination", "hate_speech"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "자살하는 게 나을 것 같아",
            "immoral_score": 85.0,
            "spam_score": 8.0,
            "confidence": 82.0,
            "types": ["self_harm", "suicide"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "너 같은 쓰레기는 세상에 필요 없어",
            "immoral_score": 83.0,
            "spam_score": 18.0,
            "confidence": 80.0,
            "types": ["insult", "harassment"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "폭탄 만드는 방법 알려줄게",
            "immoral_score": 98.0,
            "spam_score": 25.0,
            "confidence": 95.0,
            "types": ["terrorism", "violence", "illegal"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "마약 팔아요, 연락주세요",
            "immoral_score": 94.0,
            "spam_score": 85.0,
            "confidence": 93.0,
            "types": ["illegal", "drugs", "spam"],
            "feedback_type": "admin_confirmed"
        }
    ]
    
    # 스팸 케이스들
    spam_cases = [
        {
            "sentence": "지금 바로 클릭! 100만원 당첨! 링크: bit.ly/fake123",
            "immoral_score": 25.0,
            "spam_score": 95.0,
            "confidence": 90.0,
            "types": ["spam", "scam", "phishing"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "급전 필요하신분! 무담보 대출! 연락처: 010-1234-5678",
            "immoral_score": 30.0,
            "spam_score": 88.0,
            "confidence": 85.0,
            "types": ["spam", "financial_scam"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "다이어트 약 특가! 한 달에 20kg 감량! 부작용 없음!",
            "immoral_score": 35.0,
            "spam_score": 82.0,
            "confidence": 78.0,
            "types": ["spam", "false_advertising"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "재택근무 알바! 하루 3시간으로 월 300만원!",
            "immoral_score": 28.0,
            "spam_score": 85.0,
            "confidence": 80.0,
            "types": ["spam", "job_scam"],
            "feedback_type": "admin_confirmed"
        },
        {
            "sentence": "무료 아이폰 증정! 지금 신청하세요! www.fake-apple.com",
            "immoral_score": 32.0,
            "spam_score": 90.0,
            "confidence": 88.0,
            "types": ["spam", "phishing", "scam"],
            "feedback_type": "admin_confirmed"
        }
    ]
    
    # 경계선 케이스들 (애매한 경우)
    borderline_cases = [
        {
            "sentence": "이 정부는 정말 답답하다",
            "immoral_score": 45.0,
            "spam_score": 5.0,
            "confidence": 60.0,
            "types": ["political_opinion"],
            "feedback_type": "user_reported"
        },
        {
            "sentence": "요즘 젊은 애들은 예의가 없어",
            "immoral_score": 55.0,
            "spam_score": 8.0,
            "confidence": 65.0,
            "types": ["generational_conflict"],
            "feedback_type": "user_reported"
        },
        {
            "sentence": "이 회사 제품 진짜 별로야, 돈 아까워",
            "immoral_score": 35.0,
            "spam_score": 15.0,
            "confidence": 55.0,
            "types": ["negative_review"],
            "feedback_type": "user_reported"
        },
        {
            "sentence": "살 빼려면 운동해야지, 게으르면 안 돼",
            "immoral_score": 40.0,
            "spam_score": 10.0,
            "confidence": 50.0,
            "types": ["body_shaming"],
            "feedback_type": "user_reported"
        }
    ]
    
    # 정상 케이스들 (오탐지 방지용)
    normal_cases = [
        {
            "sentence": "오늘 날씨가 정말 좋네요",
            "immoral_score": 5.0,
            "spam_score": 2.0,
            "confidence": 95.0,
            "types": ["normal"],
            "feedback_type": "auto_saved"
        },
        {
            "sentence": "맛있는 저녁 먹었어요",
            "immoral_score": 3.0,
            "spam_score": 1.0,
            "confidence": 97.0,
            "types": ["normal"],
            "feedback_type": "auto_saved"
        },
        {
            "sentence": "새로운 책을 읽고 있습니다",
            "immoral_score": 2.0,
            "spam_score": 1.0,
            "confidence": 98.0,
            "types": ["normal"],
            "feedback_type": "auto_saved"
        },
        {
            "sentence": "친구와 영화를 보러 갔어요",
            "immoral_score": 4.0,
            "spam_score": 2.0,
            "confidence": 96.0,
            "types": ["normal"],
            "feedback_type": "auto_saved"
        }
    ]
    
    return immoral_cases + spam_cases + borderline_cases + normal_cases


def create_dummy_embedding(dimension=1536):
    """더미 임베딩 벡터 생성 (실제로는 OpenAI API 사용)"""
    return [random.uniform(-1, 1) for _ in range(dimension)]


def populate_chroma_data():
    """ChromaDB에 샘플 데이터 추가"""
    
    try:
        from ethics.ethics_vector_db import get_client, upsert_confirmed_case, get_collection_stats
        
        print("=" * 60)
        print("ChromaDB 데이터 추가 시작")
        print("=" * 60)
        
        # 클라이언트 생성
        client = get_client()
        print("[INFO] ChromaDB 클라이언트 연결 성공")
        
        # 초기 상태 확인
        initial_stats = get_collection_stats(client)
        print(f"[INFO] 초기 문서 수: {initial_stats['total_documents']}")
        
        # 샘플 케이스 생성
        sample_cases = generate_sample_cases()
        print(f"[INFO] 생성된 샘플 케이스 수: {len(sample_cases)}")
        
        # 데이터 추가
        added_count = 0
        for i, case in enumerate(sample_cases):
            try:
                # 더미 임베딩 생성 (실제로는 OpenAI API 사용)
                embedding = create_dummy_embedding()
                
                # 메타데이터 구성
                metadata = {
                    "sentence": case["sentence"],
                    "immoral_score": case["immoral_score"],
                    "spam_score": case["spam_score"],
                    "confidence": case["confidence"],
                    "confirmed": case["feedback_type"] == "admin_confirmed",
                    "post_id": f"sample_post_{i+1:03d}",
                    "user_id": f"sample_user_{random.randint(1, 100)}",
                    "created_at": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                    "feedback_type": case["feedback_type"],
                    "admin_id": "admin_sample" if case["feedback_type"] == "admin_confirmed" else "",
                    "admin_action": "approve" if case["feedback_type"] == "admin_confirmed" else "",
                    "original_immoral_score": case["immoral_score"] - random.uniform(-5, 5),
                    "original_spam_score": case["spam_score"] - random.uniform(-5, 5),
                    "note": f"Sample case for {', '.join(case['types'])}"
                }
                
                # ChromaDB에 추가
                upsert_confirmed_case(client, embedding, metadata)
                added_count += 1
                
                if (i + 1) % 5 == 0:
                    print(f"[PROGRESS] {i + 1}/{len(sample_cases)} 케이스 추가 완료")
                
            except Exception as e:
                print(f"[ERROR] 케이스 {i+1} 추가 실패: {e}")
                continue
        
        # 최종 상태 확인
        final_stats = get_collection_stats(client)
        print(f"\n[SUCCESS] 데이터 추가 완료!")
        print(f"  - 추가된 케이스 수: {added_count}")
        print(f"  - 최종 문서 수: {final_stats['total_documents']}")
        print(f"  - 관리자 확정 케이스: {final_stats.get('confirmed_count', 0)}")
        print(f"  - 미확정 케이스: {final_stats.get('unconfirmed_count', 0)}")
        print(f"  - 평균 비윤리점수: {final_stats.get('avg_immoral_score', 0):.1f}")
        print(f"  - 평균 스팸점수: {final_stats.get('avg_spam_score', 0):.1f}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 데이터 추가 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_functionality():
    """추가된 데이터로 검색 기능 테스트"""
    
    print("\n" + "=" * 60)
    print("검색 기능 테스트")
    print("=" * 60)
    
    try:
        from ethics.ethics_vector_db import get_client, search_similar_cases
        
        client = get_client()
        
        # 테스트 쿼리들
        test_queries = [
            {
                "description": "폭력적 위협",
                "embedding": create_dummy_embedding(),
                "expected_types": ["threat", "violence"]
            },
            {
                "description": "스팸/사기",
                "embedding": create_dummy_embedding(),
                "expected_types": ["spam", "scam"]
            },
            {
                "description": "차별 발언",
                "embedding": create_dummy_embedding(),
                "expected_types": ["discrimination"]
            }
        ]
        
        for i, query in enumerate(test_queries):
            print(f"\n[TEST {i+1}] {query['description']} 관련 케이스 검색:")
            
            similar_cases = search_similar_cases(
                client=client,
                embedding=query["embedding"],
                top_k=3,
                min_score=0.0,
                min_confidence=0.0
            )
            
            if similar_cases:
                for j, case in enumerate(similar_cases):
                    print(f"  {j+1}. 유사도: {case['score']:.3f}")
                    print(f"     문장: {case['document'][:50]}...")
                    print(f"     비윤리: {case['metadata'].get('immoral_score', 0):.1f}")
                    print(f"     스팸: {case['metadata'].get('spam_score', 0):.1f}")
            else:
                print("  검색 결과 없음")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 검색 테스트 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    
    print("ChromaDB 데이터 추가 및 테스트 스크립트")
    
    # 1. 데이터 추가
    success = populate_chroma_data()
    
    if success:
        # 2. 검색 기능 테스트
        test_search_functionality()
        
        print("\n" + "=" * 60)
        print("모든 작업이 완료되었습니다!")
        print("이제 웹 대시보드에서 RAG 통계를 확인해보세요.")
        print("=" * 60)
    else:
        print("\n데이터 추가에 실패했습니다.")


if __name__ == "__main__":
    main()
