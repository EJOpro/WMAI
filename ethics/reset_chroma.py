"""
ChromaDB 재초기화 스크립트
기존 ChromaDB 데이터를 완전히 삭제하고 새로 초기화합니다.
"""

import os
import shutil
from typing import Dict, Any

def reset_chroma_db() -> Dict[str, Any]:
    """
    ChromaDB를 완전히 재초기화합니다.
    
    Returns:
        Dict: 재초기화 결과
    """
    result = {
        "success": False,
        "message": "",
        "details": {}
    }
    
    try:
        # 기존 ChromaDB 디렉토리 경로
        chroma_dir = "./ethics_chroma_store"
        
        print(f"[INFO] ChromaDB 재초기화 시작...")
        
        # 1. 기존 디렉토리 삭제
        if os.path.exists(chroma_dir):
            print(f"[INFO] 기존 ChromaDB 디렉토리 삭제 중: {chroma_dir}")
            try:
                shutil.rmtree(chroma_dir)
                print(f"[INFO] 기존 ChromaDB 디렉토리 삭제 완료")
                result["details"]["old_directory_removed"] = True
            except Exception as e:
                print(f"[WARN] 기존 디렉토리 삭제 중 오류: {e}")
                result["details"]["old_directory_removed"] = False
                result["details"]["removal_error"] = str(e)
        else:
            print(f"[INFO] 기존 ChromaDB 디렉토리가 존재하지 않음")
            result["details"]["old_directory_removed"] = True
        
        # 2. 새 ChromaDB 클라이언트 생성
        print(f"[INFO] 새 ChromaDB 클라이언트 생성 중...")
        
        try:
            from ethics.ethics_vector_db import get_client, get_collection, COLLECTION_NAME
            
            # 클라이언트 생성
            client = get_client()
            print(f"[INFO] ChromaDB 클라이언트 생성 성공")
            
            # 컬렉션 생성
            collection = get_collection(client, COLLECTION_NAME)
            print(f"[INFO] 컬렉션 생성 성공: {collection.name}")
            
            # 상태 확인
            count = collection.count()
            print(f"[INFO] 현재 문서 수: {count}")
            
            result["details"].update({
                "client_created": True,
                "collection_name": collection.name,
                "document_count": count,
                "collection_created": True
            })
            
            result["success"] = True
            result["message"] = "ChromaDB 재초기화 완료"
            
        except Exception as e:
            print(f"[ERROR] ChromaDB 클라이언트 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            
            result["details"].update({
                "client_created": False,
                "client_error": str(e)
            })
            result["message"] = f"ChromaDB 클라이언트 생성 실패: {e}"
            
    except Exception as e:
        print(f"[ERROR] ChromaDB 재초기화 중 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        
        result["message"] = f"재초기화 중 오류: {e}"
        result["details"]["unexpected_error"] = str(e)
    
    return result


def test_chroma_connection() -> Dict[str, Any]:
    """
    ChromaDB 연결 테스트
    
    Returns:
        Dict: 테스트 결과
    """
    result = {
        "success": False,
        "message": "",
        "details": {}
    }
    
    try:
        print("[INFO] ChromaDB 연결 테스트 시작...")
        
        from ethics.ethics_vector_db import get_client, get_collection_stats, COLLECTION_NAME
        
        # 클라이언트 생성 테스트
        client = get_client()
        print("[INFO] 클라이언트 생성 성공")
        
        # 통계 조회 테스트
        stats = get_collection_stats(client, COLLECTION_NAME)
        print(f"[INFO] 통계 조회 성공: {stats}")
        
        result.update({
            "success": True,
            "message": "ChromaDB 연결 테스트 성공",
            "details": {
                "client_created": True,
                "stats": stats
            }
        })
        
    except Exception as e:
        print(f"[ERROR] ChromaDB 연결 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        
        result.update({
            "success": False,
            "message": f"ChromaDB 연결 테스트 실패: {e}",
            "details": {
                "error": str(e)
            }
        })
    
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("ChromaDB 재초기화 스크립트")
    print("=" * 60)
    
    # 1. 연결 테스트
    print("\n1. 현재 상태 테스트...")
    test_result = test_chroma_connection()
    print(f"테스트 결과: {test_result['message']}")
    
    # 2. 재초기화 실행
    print("\n2. ChromaDB 재초기화...")
    reset_result = reset_chroma_db()
    print(f"재초기화 결과: {reset_result['message']}")
    
    # 3. 재초기화 후 테스트
    if reset_result["success"]:
        print("\n3. 재초기화 후 테스트...")
        final_test = test_chroma_connection()
        print(f"최종 테스트 결과: {final_test['message']}")
    
    print("\n" + "=" * 60)
    print("스크립트 실행 완료")
    print("=" * 60)
