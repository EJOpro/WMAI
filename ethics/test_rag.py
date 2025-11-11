"""
RAG 기능 테스트 스크립트
ChromaDB 연결 및 기본 기능을 테스트합니다.
"""

import sys
import os

# PYTHONPATH 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_basic_connection():
    """기본 연결 테스트"""
    print("=== 기본 연결 테스트 ===")
    
    try:
        from ethics.ethics_vector_db import get_client, get_collection_stats, COLLECTION_NAME
        
        # 클라이언트 생성
        client = get_client()
        print("[OK] ChromaDB 클라이언트 생성 성공")
        
        # 통계 조회
        stats = get_collection_stats(client, COLLECTION_NAME)
        print(f"[OK] 통계 조회 성공: {stats}")
        
        return True, stats
        
    except Exception as e:
        print(f"[FAIL] 기본 연결 테스트 실패: {e}")
        return False, None


def test_sample_data_insertion():
    """샘플 데이터 삽입 테스트"""
    print("\n=== 샘플 데이터 삽입 테스트 ===")
    
    try:
        from ethics.ethics_vector_db import get_client, upsert_confirmed_case, get_collection_stats
        from datetime import datetime
        
        client = get_client()
        
        # 샘플 임베딩 (1536차원 더미 벡터)
        sample_embedding = [0.1] * 1536
        
        # 샘플 메타데이터
        sample_metadata = {
            "sentence": "테스트 문장입니다.",
            "immoral_score": 75.0,
            "spam_score": 60.0,
            "confidence": 85.0,
            "confirmed": True,
            "post_id": "test_post_001",
            "user_id": "test_user",
            "created_at": datetime.now().isoformat(),
            "feedback_type": "manual_test",
            "admin_id": "admin_test"
        }
        
        # 데이터 삽입
        upsert_confirmed_case(client, sample_embedding, sample_metadata)
        print("[OK] 샘플 데이터 삽입 성공")
        
        # 삽입 후 통계 확인
        stats = get_collection_stats(client)
        print(f"[OK] 삽입 후 통계: {stats}")
        
        return True, stats
        
    except Exception as e:
        print(f"[FAIL] 샘플 데이터 삽입 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_search_functionality():
    """검색 기능 테스트"""
    print("\n=== 검색 기능 테스트 ===")
    
    try:
        from ethics.ethics_vector_db import get_client, search_similar_cases
        
        client = get_client()
        
        # 검색용 더미 임베딩
        search_embedding = [0.1] * 1536
        
        # 유사 케이스 검색
        similar_cases = search_similar_cases(
            client=client,
            embedding=search_embedding,
            top_k=3,
            min_score=0.0,  # 낮은 임계값으로 설정
            min_confidence=0.0
        )
        
        print(f"[OK] 검색 성공: {len(similar_cases)}개 케이스 발견")
        for i, case in enumerate(similar_cases):
            print(f"  {i+1}. 유사도: {case['score']:.3f}, 문장: {case['document'][:50]}...")
        
        return True, similar_cases
        
    except Exception as e:
        print(f"[FAIL] 검색 기능 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    """메인 테스트 함수"""
    print("RAG 기능 테스트 시작")
    print("=" * 50)
    
    # 1. 기본 연결 테스트
    connection_ok, initial_stats = test_basic_connection()
    if not connection_ok:
        print("기본 연결 테스트 실패. 테스트를 중단합니다.")
        return
    
    # 2. 샘플 데이터 삽입 테스트
    insertion_ok, post_stats = test_sample_data_insertion()
    
    # 3. 검색 기능 테스트
    if insertion_ok:
        search_ok, search_results = test_search_functionality()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    print(f"[결과] 기본 연결: {'성공' if connection_ok else '실패'}")
    print(f"[결과] 데이터 삽입: {'성공' if insertion_ok else '실패'}")
    if insertion_ok:
        print(f"[결과] 검색 기능: {'성공' if search_ok else '실패'}")
    
    if initial_stats:
        print(f"\n초기 상태: {initial_stats['status']}, 문서 수: {initial_stats['total_documents']}")
    if post_stats:
        print(f"삽입 후: {post_stats['status']}, 문서 수: {post_stats['total_documents']}")
    
    print("=" * 50)


if __name__ == "__main__":
    main()
