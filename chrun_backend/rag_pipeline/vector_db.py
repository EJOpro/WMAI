"""
벡터 데이터베이스 모듈 - ChromaDB를 사용한 확인된 이탈 위험 문장 저장 및 검색

이 모듈은 확인된(confirmed) 이탈 위험 문장들을 벡터DB에 영구 저장하고,
새로운 글이 들어올 때 유사한 문장을 검색할 수 있는 기능을 제공합니다.
"""

import hashlib
import json
import os
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ChromaDB lazy import - pydantic 버전 충돌 우회
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ChromaDB import 실패: {e}. 벡터 검색 기능이 비활성화됩니다.")
    chromadb = None
    Settings = None
    CHROMADB_AVAILABLE = False


def get_client(persist_dir: str = "./chroma_store") -> Any:
    """
    ChromaDB 클라이언트를 생성하고 반환합니다.
    
    Args:
        persist_dir (str): 데이터를 저장할 디렉토리 경로 (기본값: "./chroma_store")
        
    Returns:
        chromadb.ClientAPI: ChromaDB 클라이언트 인스턴스
    """
    if not CHROMADB_AVAILABLE:
        logger.error("ChromaDB를 사용할 수 없습니다. 클라이언트를 생성할 수 없습니다.")
        return None
    
    absolute_path = os.path.abspath(persist_dir)
    os.makedirs(absolute_path, exist_ok=True)

    client = chromadb.PersistentClient(
        path=absolute_path,
        settings=Settings(
            anonymized_telemetry=False,  # 텔레메트리 비활성화
            allow_reset=True  # 개발 환경에서 리셋 허용
        )
    )
    return client


def get_collection(client: Any, name: str = "confirmed_risk") -> Any:
    """
    지정된 이름의 컬렉션을 생성하거나 기존 컬렉션을 반환합니다.
    
    Args:
        client (chromadb.ClientAPI): ChromaDB 클라이언트
        name (str): 컬렉션 이름 (기본값: "confirmed_risk")
        
    Returns:
        chromadb.Collection: ChromaDB 컬렉션 인스턴스
    """
    try:
        # 기존 컬렉션이 있으면 반환
        collection = client.get_collection(name=name)
    except (ValueError, Exception):
        # 컬렉션이 없으면 새로 생성
        collection = client.create_collection(
            name=name,
            metadata={"description": "확인된 이탈 위험 문장들을 저장하는 컬렉션"}
        )
    
    return collection


def build_chunk_id(sentence: str, post_id: str) -> str:
    """
    문장과 게시물 ID를 기반으로 안정적인 해시 ID를 생성합니다.
    
    Args:
        sentence (str): 문장 내용
        post_id (str): 게시물 ID
        
    Returns:
        str: SHA-256 해시 기반의 고유 ID
    """
    # 문장과 post_id를 결합하여 고유한 식별자 생성
    combined_text = f"{sentence.strip()}|{post_id}"
    
    # SHA-256 해시로 안정적인 ID 생성
    chunk_id = hashlib.sha256(combined_text.encode('utf-8')).hexdigest()
    
    return chunk_id


def upsert_confirmed_chunk(
    client: chromadb.ClientAPI,
    embedding: List[float], 
    meta: Dict,
    collection_name: str = "confirmed_risk"
) -> None:
    """
    확인된 이탈 위험 문장을 벡터DB에 저장합니다 (idempotent upsert).
    
    Args:
        client (chromadb.ClientAPI): ChromaDB 클라이언트
        embedding (List[float]): 문장의 임베딩 벡터
        meta (Dict): 메타데이터 (chunk_id, user_id, post_id, sentence, risk_score, created_at, confirmed 포함)
        collection_name (str): 컬렉션 이름 (기본값: "confirmed_risk")
        
    메타데이터 예시:
        {
            "chunk_id": "해시ID",
            "user_id": "사용자ID", 
            "post_id": "게시물ID",
            "sentence": "문장내용",
            "risk_score": 0.85,
            "created_at": "2024-01-01T00:00:00",
            "confirmed": True
        }
    """
    collection = get_collection(client, collection_name)
    
    chunk_id = meta.get("chunk_id")
    if not chunk_id:
        raise ValueError("메타데이터에 chunk_id가 필요합니다.")
    
    # 메타데이터 검증 및 기본값 설정
    validated_meta = {
        "chunk_id": chunk_id,
        "user_id": meta.get("user_id", ""),
        "post_id": meta.get("post_id", ""),
        "sentence": meta.get("sentence", ""),
        "risk_score": float(meta.get("risk_score", 0.0)),
        "created_at": meta.get("created_at", datetime.now().isoformat()),
        "confirmed": bool(meta.get("confirmed", True))
    }
    
    # 추가 메타데이터 필드 (있는 경우만 추가)
    optional_fields = [
        # 기존 필드
        "embed_model_v", "embed_dimension", "ts",
        "who_labeled", "segment", "reason",
        "risk_level", "risk_factors", "sentence_index", "analyzed_at",
        
        # ⭐ 문맥 정보 (KSS + 메타데이터 강화)
        "prev_sentence",           # 이전 문장
        "next_sentence",           # 다음 문장
        "total_sentences",         # 전체 문장 수
        "is_first",                # 첫 문장 여부
        "is_last",                 # 마지막 문장 여부
        "splitter_method",         # 분할 방법 (kss/regex)
        
        # ⭐ 사용자 컨텍스트
        "user_activity_trend",     # 활동 추이
        "user_prev_posts_count",   # 이전 게시글 수
        "user_join_date",          # 가입일
        "user_recent_activity_score",  # 최근 활동 점수
        
        # ⭐ 이탈 분석 메타데이터 (LLM 분석 결과)
        "churn_stage",             # 이탈 단계 (1-5단계)
        "belongingness",           # 소속감 (강함/보통/약함/없음)
        "emotion",                 # 감정 (만족/무관심/짜증/실망/포기)
        "urgency",                 # 긴급성 (IMMEDIATE/SOON/EVENTUAL/UNCLEAR)
        "recovery_chance",         # 회복 가능성 (HIGH/MEDIUM/LOW)
        
        # 임베딩 관련
        "embedding_method",        # 임베딩 방법 (basic/contextual/metadata)
        "context_format"           # 문맥 포맷 (structured/natural/separator)
    ]
    for field in optional_fields:
        if field in meta:
            validated_meta[field] = meta[field]
    
    # ChromaDB에 upsert (동일 ID면 업데이트, 없으면 추가)
    upsert_start = time.perf_counter()
    collection.upsert(
        ids=[chunk_id],
        embeddings=[embedding],
        metadatas=[validated_meta],
        documents=[validated_meta["sentence"]]  # 문장을 document로 저장
    )
    upsert_elapsed = (time.perf_counter() - upsert_start) * 1000
    logger.info("[VectorDB] upsert 완료: %s (%.2f ms)", chunk_id, upsert_elapsed)


def search_similar(
    client: chromadb.ClientAPI,
    embedding: List[float], 
    top_k: int = 5, 
    min_score: float = 0.3,
    collection_name: str = "confirmed_risk"
) -> List[Dict]:
    """
    주어진 임베딩과 유사한 확인된 이탈 위험 문장들을 검색합니다.
    
    Args:
        client (chromadb.ClientAPI): ChromaDB 클라이언트
        embedding (List[float]): 검색할 문장의 임베딩 벡터
        top_k (int): 반환할 최대 결과 수 (기본값: 5)
        min_score (float): 최소 유사도 점수 (기본값: 0.3)
        collection_name (str): 컬렉션 이름 (기본값: "confirmed_risk")
        
    Returns:
        List[Dict]: 유사한 문장들의 리스트, 각 항목은 다음을 포함:
            - id: chunk_id
            - score: 유사도 점수 (1 - distance)
            - metadata: 저장된 메타데이터
            - document: 문장 내용
    """
    collection = get_collection(client, collection_name)
    
    # 컬렉션이 비어있는지 확인
    count = collection.count()
    if count == 0:
        return []
    
    # 유사도 검색 수행
    query_start = time.perf_counter()
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, count),  # 저장된 문서 수보다 많이 요청하지 않도록
        include=["metadatas", "documents", "distances"]
    )
    query_elapsed = (time.perf_counter() - query_start) * 1000
    logger.info("[VectorDB] 검색 수행 (top_k=%d, elapsed=%.2f ms)", top_k, query_elapsed)
    
    # 결과 포맷팅
    formatted_results = []
    
    if results["ids"] and len(results["ids"]) > 0:
        ids = results["ids"][0]
        distances = results["distances"][0] if results["distances"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        documents = results["documents"][0] if results["documents"] else []
        
        for i, chunk_id in enumerate(ids):
            # ChromaDB는 거리(distance)를 반환하므로 유사도 점수로 변환
            # 거리가 작을수록 유사함 (0에 가까울수록 유사)
            distance = distances[i] if i < len(distances) else 1.0
            similarity_score = 1.0 - distance  # 유사도 점수로 변환
            
            # 최소 점수 필터링
            if similarity_score >= min_score:
                result_item = {
                    "id": chunk_id,
                    "score": similarity_score,
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "document": documents[i] if i < len(documents) else ""
                }
                formatted_results.append(result_item)
    
    # 유사도 점수 내림차순으로 정렬
    formatted_results.sort(key=lambda x: x["score"], reverse=True)
    
    return formatted_results


def get_collection_stats(client: chromadb.ClientAPI, collection_name: str = "confirmed_risk") -> Dict:
    """
    컬렉션의 통계 정보를 반환합니다.
    
    Args:
        client (chromadb.ClientAPI): ChromaDB 클라이언트
        collection_name (str): 컬렉션 이름
        
    Returns:
        Dict: 컬렉션 통계 정보
    """
    try:
        collection = get_collection(client, collection_name)
        count = collection.count()
        
        return {
            "collection_name": collection_name,
            "total_documents": count,
            "status": "active" if count > 0 else "empty"
        }
    except Exception as e:
        return {
            "collection_name": collection_name,
            "total_documents": 0,
            "status": "error",
            "error": str(e)
        }


def delete_chunk(client: chromadb.ClientAPI, chunk_id: str, collection_name: str = "confirmed_risk") -> bool:
    """
    특정 chunk를 삭제합니다.
    
    Args:
        client (chromadb.ClientAPI): ChromaDB 클라이언트
        chunk_id (str): 삭제할 chunk의 ID
        collection_name (str): 컬렉션 이름
        
    Returns:
        bool: 삭제 성공 여부
    """
    try:
        collection = get_collection(client, collection_name)
        collection.delete(ids=[chunk_id])
        return True
    except Exception:
        return False
