"""
Ethics 벡터 데이터베이스 모듈
ChromaDB를 사용한 비윤리/스팸 케이스 저장 및 검색
독립적으로 구현 (chrun_backend 참조 없음)
"""

import hashlib
from typing import Dict, List, Optional
from datetime import datetime

import chromadb
from chromadb.config import Settings


# ChromaDB 저장 경로 (독립적)
PERSIST_DIR = "./ethics_chroma_store"
COLLECTION_NAME = "ethics_spam_cases"


def get_client() -> chromadb.ClientAPI:
    """
    ChromaDB 클라이언트를 생성하고 반환합니다.
    
    Returns:
        chromadb.ClientAPI: ChromaDB 클라이언트 인스턴스
    """
    client = chromadb.PersistentClient(
        path=PERSIST_DIR,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    return client


def get_collection(client: chromadb.ClientAPI, name: str = COLLECTION_NAME) -> chromadb.Collection:
    """
    지정된 이름의 컬렉션을 생성하거나 기존 컬렉션을 반환합니다.
    
    Args:
        client (chromadb.ClientAPI): ChromaDB 클라이언트
        name (str): 컬렉션 이름 (기본값: "ethics_spam_cases")
        
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
            metadata={"description": "비윤리/스팸 케이스들을 저장하는 컬렉션"}
        )
    
    return collection


def build_chunk_id(sentence: str, post_id: str = "") -> str:
    """
    문장과 게시물 ID를 기반으로 안정적인 해시 ID를 생성합니다.
    
    Args:
        sentence (str): 문장 내용
        post_id (str): 게시물 ID (선택)
        
    Returns:
        str: SHA-256 해시 기반의 고유 ID
    """
    combined_text = f"{sentence.strip()}|{post_id}"
    chunk_id = hashlib.sha256(combined_text.encode('utf-8')).hexdigest()
    return chunk_id


def upsert_confirmed_case(
    client: chromadb.ClientAPI,
    embedding: List[float],
    metadata: Dict,
    collection_name: str = COLLECTION_NAME
) -> None:
    """
    확인된 비윤리/스팸 케이스를 벡터DB에 저장합니다 (idempotent upsert).
    
    Args:
        client (chromadb.ClientAPI): ChromaDB 클라이언트
        embedding (List[float]): 문장의 임베딩 벡터
        metadata (Dict): 메타데이터
            필수 필드:
            - sentence: 문장 내용
            - immoral_score: 비윤리 점수 (0-100)
            - spam_score: 스팸 점수 (0-100)
            - confidence: 신뢰도 (0-100)
            - confirmed: 관리자 확인 여부 (bool)
            선택 필드:
            - post_id: 게시물 ID
            - user_id: 사용자 ID
            - created_at: 생성 시간 (ISO 형식)
            - feedback_type: 피드백 유형
            - admin_id: 관리자 ID
        collection_name (str): 컬렉션 이름
    """
    collection = get_collection(client, collection_name)
    
    sentence = metadata.get("sentence", "")
    if not sentence:
        raise ValueError("메타데이터에 sentence가 필요합니다.")
    
    post_id = metadata.get("post_id", "")
    chunk_id = build_chunk_id(sentence, post_id)
    
    # 메타데이터 검증 및 기본값 설정
    validated_meta = {
        "chunk_id": chunk_id,
        "sentence": sentence,
        "immoral_score": float(metadata.get("immoral_score", 0.0)),
        "spam_score": float(metadata.get("spam_score", 0.0)),
        "immoral_confidence": float(metadata.get("immoral_confidence", 0.0)),
        "spam_confidence": float(metadata.get("spam_confidence", 0.0)),
        "confidence": float(metadata.get("confidence", 0.0)),
        "confirmed": bool(metadata.get("confirmed", False)),
        "post_id": metadata.get("post_id", ""),
        "user_id": metadata.get("user_id", ""),
        "created_at": metadata.get("created_at", datetime.now().isoformat()),
        "feedback_type": metadata.get("feedback_type", "auto_saved"),
        "admin_id": str(metadata.get("admin_id", "")),
        "admin_action": metadata.get("admin_action", ""),
        "original_immoral_score": float(metadata.get("original_immoral_score", 0.0)),
        "original_spam_score": float(metadata.get("original_spam_score", 0.0)),
        "note": metadata.get("note", "")
    }
    
    # ChromaDB에 upsert (동일 ID면 업데이트, 없으면 추가)
    collection.upsert(
        ids=[chunk_id],
        embeddings=[embedding],
        metadatas=[validated_meta],
        documents=[sentence]  # 문장을 document로 저장
    )


def search_similar_cases(
    client: chromadb.ClientAPI,
    embedding: List[float],
    top_k: int = 5,
    min_score: float = 0.5,
    min_confidence: float = 70.0,
    prefer_confirmed: bool = True,
    collection_name: str = COLLECTION_NAME
) -> List[Dict]:
    """
    주어진 임베딩과 유사한 비윤리/스팸 케이스들을 검색합니다.
    
    Args:
        client (chromadb.ClientAPI): ChromaDB 클라이언트
        embedding (List[float]): 검색할 문장의 임베딩 벡터
        top_k (int): 반환할 최대 결과 수 (기본값: 5)
        min_score (float): 최소 유사도 점수 (기본값: 0.5)
        min_confidence (float): 최소 신뢰도 (기본값: 70.0)
        prefer_confirmed (bool): 관리자 확인된 케이스 우선 사용 (기본값: True)
        collection_name (str): 컬렉션 이름
        
    Returns:
        List[Dict]: 유사한 케이스들의 리스트, 각 항목은 다음을 포함:
            - id: chunk_id
            - score: 유사도 점수 (0-1)
            - metadata: 저장된 메타데이터
            - document: 문장 내용
    """
    collection = get_collection(client, collection_name)
    
    # 컬렉션이 비어있는지 확인
    count = collection.count()
    if count == 0:
        return []
    
    # 유사도 검색 수행 (더 많이 검색하여 필터링)
    search_k = min(top_k * 3, count)  # 필터링을 위해 더 많이 검색
    
    results = collection.query(
        query_embeddings=[embedding],
        n_results=search_k,
        include=["metadatas", "documents", "distances"]
    )
    
    # 결과 포맷팅 및 필터링
    formatted_results = []
    
    if results["ids"] and len(results["ids"]) > 0:
        ids = results["ids"][0]
        distances = results["distances"][0] if results["distances"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        documents = results["documents"][0] if results["documents"] else []
        
        for i, chunk_id in enumerate(ids):
            # ChromaDB는 거리(distance)를 반환하므로 유사도 점수로 변환
            distance = distances[i] if i < len(distances) else 1.0
            similarity_score = 1.0 - distance  # 유사도 점수로 변환
            
            # 최소 점수 필터링
            if similarity_score < min_score:
                continue
            
            metadata = metadatas[i] if i < len(metadatas) else {}
            confidence = float(metadata.get("confidence", 0.0))
            
            # 최소 신뢰도 필터링
            if confidence < min_confidence:
                continue
            
            result_item = {
                "id": chunk_id,
                "score": similarity_score,
                "metadata": metadata,
                "document": documents[i] if i < len(documents) else "",
                "confirmed": bool(metadata.get("confirmed", False)),
                "confidence": confidence
            }
            formatted_results.append(result_item)
    
    # 관리자 확인된 케이스 우선 정렬
    if prefer_confirmed:
        formatted_results.sort(
            key=lambda x: (x["confirmed"], x["score"]),
            reverse=True
        )
    else:
        # 유사도 점수 내림차순으로 정렬
        formatted_results.sort(key=lambda x: x["score"], reverse=True)
    
    # 상위 top_k개만 반환
    return formatted_results[:top_k]


def get_collection_stats(
    client: chromadb.ClientAPI,
    collection_name: str = COLLECTION_NAME
) -> Dict:
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
        
        stats = {
            "collection_name": collection_name,
            "total_documents": count,
            "status": "active" if count > 0 else "empty"
        }
        
        # 추가 통계 계산
        if count > 0:
            all_data = collection.get(include=['metadatas'])
            metadatas = all_data.get('metadatas', [])
            
            if metadatas:
                # 관리자 확인된 케이스 수
                confirmed_count = sum(
                    1 for meta in metadatas 
                    if bool(meta.get('confirmed', False))
                )
                
                # 평균 점수 계산
                immoral_scores = [
                    float(meta.get('immoral_score', 0)) 
                    for meta in metadatas
                ]
                spam_scores = [
                    float(meta.get('spam_score', 0)) 
                    for meta in metadatas
                ]
                confidences = [
                    float(meta.get('confidence', 0)) 
                    for meta in metadatas
                ]
                
                stats.update({
                    "confirmed_count": confirmed_count,
                    "unconfirmed_count": count - confirmed_count,
                    "avg_immoral_score": sum(immoral_scores) / len(immoral_scores) if immoral_scores else 0.0,
                    "avg_spam_score": sum(spam_scores) / len(spam_scores) if spam_scores else 0.0,
                    "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0
                })
        
        return stats
        
    except Exception as e:
        return {
            "collection_name": collection_name,
            "total_documents": 0,
            "status": "error",
            "error": str(e)
        }


def delete_case(
    client: chromadb.ClientAPI,
    chunk_id: str,
    collection_name: str = COLLECTION_NAME
) -> bool:
    """
    특정 케이스를 삭제합니다.
    
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


def get_all_cases(
    client: chromadb.ClientAPI,
    limit: int = 50,
    offset: int = 0,
    collection_name: str = COLLECTION_NAME
) -> List[Dict]:
    """
    벡터DB의 모든 케이스를 조회합니다.
    
    Args:
        client: ChromaDB 클라이언트
        limit: 조회할 최대 개수
        offset: 오프셋
        collection_name: 컬렉션 이름
        
    Returns:
        케이스 리스트
    """
    try:
        collection = get_collection(client, collection_name)
        
        # 모든 데이터 가져오기
        raw = collection.get(
            include=["metadatas", "documents"]
        )
        
        if not raw or not raw.get('ids'):
            return []
        
        # 결과 조합
        cases = []
        ids = raw['ids']
        metadatas = raw.get('metadatas', [])
        documents = raw.get('documents', [])
        
        for i, chunk_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) else {}
            document = documents[i] if i < len(documents) else ''
            
            cases.append({
                'id': chunk_id,
                'document': document,
                'metadata': metadata
            })
        
        # created_at 기준 정렬 (최신순)
        cases.sort(
            key=lambda x: x.get('metadata', {}).get('created_at', ''),
            reverse=True
        )
        
        # offset과 limit 적용
        return cases[offset:offset + limit]
        
    except Exception as e:
        print(f"[ERROR] 전체 사례 조회 실패: {e}")
        raise


def get_recent_confirmed_cases(
    client: chromadb.ClientAPI,
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    source_type: Optional[str] = None,
    collection_name: str = COLLECTION_NAME
) -> List[Dict]:
    """
    관리자가 확정한 최근 케이스들을 조회합니다.
    
    Args:
        client: ChromaDB 클라이언트
        limit: 조회할 최대 개수
        offset: 오프셋
        action: 필터링할 액션 타입 (approve/reject)
        source_type: 필터링할 소스 타입 (ethics_log/report)
        collection_name: 컬렉션 이름
        
    Returns:
        확정 케이스 리스트
    """
    try:
        collection = get_collection(client, collection_name)
        
        # 모든 데이터 가져오기 (ChromaDB는 offset을 직접 지원하지 않음)
        raw = collection.get(
            include=["metadatas", "documents"]
        )
        
        if not raw or not raw.get('ids'):
            return []
        
        # 결과 조합
        cases = []
        ids = raw['ids']
        metadatas = raw.get('metadatas', [])
        documents = raw.get('documents', [])
        
        for i, chunk_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) else {}
            document = documents[i] if i < len(documents) else ''
            
            # confirmed=True인 것만 필터링
            if not metadata.get('confirmed'):
                continue
            
            # action 필터링
            if action and metadata.get('admin_action') != action:
                continue
            
            # source_type 필터링
            if source_type and metadata.get('source_type') != source_type:
                continue
            
            cases.append({
                'id': chunk_id,
                'document': document,
                'metadata': metadata
            })
        
        # created_at 기준 정렬 (최신순)
        cases.sort(
            key=lambda x: x.get('metadata', {}).get('created_at', ''),
            reverse=True
        )
        
        # offset과 limit 적용
        return cases[offset:offset + limit]
        
    except Exception as e:
        print(f"[ERROR] confirmed 사례 조회 실패: {e}")
        raise