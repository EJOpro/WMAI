"""
벡터 데이터베이스 모듈 - ChromaDB를 사용한 확인된 이탈 위험 문장 저장 및 검색

이 모듈은 확인된(confirmed) 이탈 위험 문장들을 벡터DB에 영구 저장하고,
새로운 글이 들어올 때 유사한 문장을 검색할 수 있는 기능을 제공합니다.
"""

import hashlib
import json
from typing import Dict, List, Optional
from datetime import datetime

import chromadb
from chromadb.config import Settings


def get_client(persist_dir: str = "./chroma_store") -> chromadb.ClientAPI:
    """
    ChromaDB 클라이언트를 생성하고 반환합니다.
    
    Args:
        persist_dir (str): 데이터를 저장할 디렉토리 경로 (기본값: "./chroma_store")
        
    Returns:
        chromadb.ClientAPI: ChromaDB 클라이언트 인스턴스
    """
    client = chromadb.PersistentClient(
        path=persist_dir,
        settings=Settings(
            anonymized_telemetry=False,  # 텔레메트리 비활성화
            allow_reset=True  # 개발 환경에서 리셋 허용
        )
    )
    return client


def get_collection(client: chromadb.ClientAPI, name: str = "confirmed_risk") -> chromadb.Collection:
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
    
    # ChromaDB에 upsert (동일 ID면 업데이트, 없으면 추가)
    collection.upsert(
        ids=[chunk_id],
        embeddings=[embedding],
        metadatas=[validated_meta],
        documents=[validated_meta["sentence"]]  # 문장을 document로 저장
    )


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
    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, count),  # 저장된 문서 수보다 많이 요청하지 않도록
        include=["metadatas", "documents", "distances"]
    )
    
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
