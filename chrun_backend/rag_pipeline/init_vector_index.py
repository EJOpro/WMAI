"""
벡터 인덱스 초기화 스크립트
벡터DB 인덱스를 초기화하고 기존 데이터를 마이그레이션합니다.
"""

import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_pipeline.vector_store import get_vector_store
from rag_pipeline.embedding_service import get_embedding, EMBEDDING_MODEL, EMBEDDING_DIMENSION
from rag_pipeline.high_risk_store import get_recent_high_risk, get_chunk_by_id


def init_vector_index(
    backend: str = "chroma",
    collection_name: str = "high_risk_sentences",
    migrate_from_sqlite: bool = True,
    limit: int = 1000
) -> Dict[str, Any]:
    """
    벡터 인덱스 초기화
    
    Args:
        backend (str): 백엔드 타입 ("chroma" 또는 "faiss")
        collection_name (str): 컬렉션 이름
        migrate_from_sqlite (bool): SQLite에서 데이터 마이그레이션 여부
        limit (int): 마이그레이션할 최대 개수
        
    Returns:
        Dict[str, Any]: 초기화 결과
    """
    print(f"[INFO] 벡터 인덱스 초기화 시작: {backend}")
    print(f"[INFO] 임베딩 모델: {EMBEDDING_MODEL}, 차원: {EMBEDDING_DIMENSION}")
    
    # 벡터 스토어 연결
    vector_store = get_vector_store(backend=backend)
    
    if not vector_store.is_connected:
        return {
            "status": "error",
            "message": "벡터 스토어 연결 실패",
            "backend": backend
        }
    
    stats_before = vector_store.get_collection_stats()
    print(f"[INFO] 초기화 전 통계: {stats_before}")
    
    migrated_count = 0
    error_count = 0
    
    # SQLite에서 데이터 마이그레이션
    if migrate_from_sqlite:
        print(f"[INFO] SQLite에서 데이터 마이그레이션 시작 (최대 {limit}개)")
        
        try:
            # confirmed=true인 항목들만 가져오기
            all_chunks = get_recent_high_risk(limit=limit)
            confirmed_chunks = [c for c in all_chunks if c.get('confirmed', False)]
            
            print(f"[INFO] 마이그레이션 대상: {len(confirmed_chunks)}개 (전체 {len(all_chunks)}개 중)")
            
            for i, chunk in enumerate(confirmed_chunks, 1):
                try:
                    chunk_id = chunk.get('chunk_id', '')
                    sentence = chunk.get('sentence', '')
                    
                    if not sentence:
                        continue
                    
                    # 임베딩 생성
                    embedding = get_embedding(sentence)
                    
                    # 메타데이터 준비
                    metadata_dict = {
                        'user_id': chunk.get('user_id', ''),
                        'post_id': chunk.get('post_id', ''),
                        'sentence': sentence,
                        'risk_score': chunk.get('risk_score', 0.0),
                        'created_at': chunk.get('created_at', datetime.now().isoformat()),
                    }
                    
                    # 벡터DB에 upsert
                    vector_store.upsert_high_risk_chunk(
                        embedding=embedding,
                        metadata_dict=metadata_dict,
                        confirmed=True,
                        who_labeled="migration",
                        segment=None,
                        reason="SQLite에서 마이그레이션"
                    )
                    
                    migrated_count += 1
                    
                    if i % 10 == 0:
                        print(f"[INFO] 마이그레이션 진행 중: {i}/{len(confirmed_chunks)}")
                        
                except Exception as e:
                    error_count += 1
                    print(f"[WARN] 청크 마이그레이션 실패 ({chunk_id}): {e}")
                    continue
            
            print(f"[INFO] 마이그레이션 완료: {migrated_count}개 성공, {error_count}개 실패")
            
        except Exception as e:
            print(f"[ERROR] 마이그레이션 중 오류: {e}")
            import traceback
            traceback.print_exc()
    
    stats_after = vector_store.get_collection_stats()
    print(f"[INFO] 초기화 후 통계: {stats_after}")
    
    return {
        "status": "success",
        "backend": backend,
        "collection_name": collection_name,
        "embed_model": EMBEDDING_MODEL,
        "embed_dimension": EMBEDDING_DIMENSION,
        "migrated_count": migrated_count,
        "error_count": error_count,
        "stats_before": stats_before,
        "stats_after": stats_after
    }


def clear_vector_index(backend: str = "chroma", collection_name: str = "high_risk_sentences") -> Dict[str, Any]:
    """
    벡터 인덱스 초기화 (모든 데이터 삭제)
    
    Args:
        backend (str): 백엔드 타입
        collection_name (str): 컬렉션 이름
        
    Returns:
        Dict[str, Any]: 초기화 결과
    """
    print(f"[WARN] 벡터 인덱스 초기화 (모든 데이터 삭제): {backend}")
    
    if backend == "chroma":
        try:
            from rag_pipeline.vector_db import get_client
            client = get_client()
            try:
                collection = client.get_collection(name=collection_name)
                count = collection.count()
                client.delete_collection(name=collection_name)
                print(f"[INFO] ChromaDB 컬렉션 삭제 완료: {collection_name} ({count}개 문서)")
                return {"status": "success", "deleted_count": count}
            except Exception as e:
                print(f"[INFO] 컬렉션이 없거나 이미 삭제됨: {e}")
                return {"status": "success", "deleted_count": 0}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    elif backend == "faiss":
        index_path = f"./faiss_index_{collection_name}"
        try:
            if os.path.exists(f"{index_path}.index"):
                os.remove(f"{index_path}.index")
            if os.path.exists(f"{index_path}.meta"):
                os.remove(f"{index_path}.meta")
            print(f"[INFO] FAISS 인덱스 삭제 완료: {index_path}")
            return {"status": "success", "deleted_count": 0}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    return {"status": "error", "message": f"지원하지 않는 백엔드: {backend}"}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="벡터 인덱스 초기화 스크립트")
    parser.add_argument("--backend", choices=["chroma", "faiss"], default="chroma", help="백엔드 타입")
    parser.add_argument("--collection", default="high_risk_sentences", help="컬렉션 이름")
    parser.add_argument("--migrate", action="store_true", help="SQLite에서 데이터 마이그레이션")
    parser.add_argument("--limit", type=int, default=1000, help="마이그레이션할 최대 개수")
    parser.add_argument("--clear", action="store_true", help="인덱스 초기화 (모든 데이터 삭제)")
    
    args = parser.parse_args()
    
    if args.clear:
        result = clear_vector_index(args.backend, args.collection)
        print(f"초기화 결과: {result}")
    else:
        result = init_vector_index(
            backend=args.backend,
            collection_name=args.collection,
            migrate_from_sqlite=args.migrate,
            limit=args.limit
        )
        print(f"초기화 결과: {result}")

