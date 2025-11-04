"""
벡터 스토어 모듈
고위험 문장들을 벡터 데이터베이스에 저장하고 검색하는 기능을 제공합니다.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime


class VectorStore:
    """
    벡터 데이터베이스 인터페이스 클래스
    ChromaDB를 사용할 예정이지만 현재는 인터페이스만 정의
    """
    
    def __init__(self, collection_name: str = "high_risk_sentences"):
        """
        벡터 스토어 초기화
        
        Args:
            collection_name (str): 컬렉션 이름
        """
        self.collection_name = collection_name
        self.is_connected = False
        
        # TODO: ChromaDB 클라이언트 초기화
        # self.client = chromadb.Client()
        # self.collection = self.client.create_collection(name=collection_name)
        
    def connect(self) -> bool:
        """
        벡터 데이터베이스에 연결
        
        TODO: 실제 ChromaDB 연결 구현
        - ChromaDB 클라이언트 설정
        - 컬렉션 생성 또는 기존 컬렉션 로드
        - 연결 상태 확인
        
        Returns:
            bool: 연결 성공 여부
        """
        # 임시 구현 - 실제로는 ChromaDB 연결
        self.is_connected = True
        return True
        
    def disconnect(self) -> None:
        """
        벡터 데이터베이스 연결 해제
        
        TODO: 실제 ChromaDB 연결 해제 구현
        """
        self.is_connected = False
        
    def upsert_high_risk_chunk(
        self, 
        embedding: List[float], 
        metadata_dict: Dict[str, Any]
    ) -> None:
        """
        고위험 문장의 임베딩과 메타데이터를 벡터 DB에 저장
        
        Args:
            embedding (List[float]): 문장의 벡터 임베딩 (예: 768차원)
            metadata_dict (Dict[str, Any]): 메타데이터
                예시: {
                    "user_id": "user123",
                    "post_id": "post456", 
                    "sentence": "이 서비스 너무 싫어요. 그만둘래요.",
                    "risk_score": 0.85,
                    "created_at": datetime.now(),
                    "sentence_index": 0,
                    "risk_level": "high",
                    "risk_factors": ["고위험_키워드: 싫어", "고위험_키워드: 그만둘"]
                }
        
        TODO: 실제 ChromaDB upsert 구현
        - 임베딩 벡터와 메타데이터를 ChromaDB에 저장
        - 중복 문장 처리 (같은 user_id + post_id + sentence_index 조합)
        - 배치 처리 최적화
        """
        if not self.is_connected:
            print("[WARN] 벡터 DB에 연결되지 않음. 연결을 먼저 수행하세요.")
            return
            
        # 임시 구현 - 실제로는 ChromaDB에 저장
        print(f"[DEBUG] 고위험 문장 저장: {metadata_dict.get('sentence', '')[:50]}...")
        print(f"[DEBUG] 위험점수: {metadata_dict.get('risk_score', 0.0)}")
        print(f"[DEBUG] 임베딩 차원: {len(embedding)}")
        
        # 실제 구현 예시:
        # unique_id = f"{metadata_dict['user_id']}_{metadata_dict['post_id']}_{metadata_dict['sentence_index']}"
        # self.collection.upsert(
        #     embeddings=[embedding],
        #     metadatas=[metadata_dict],
        #     ids=[unique_id]
        # )
        
    def search_similar_chunks(
        self, 
        embedding: List[float], 
        top_k: int = 5,
        risk_score_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        주어진 임베딩과 유사한 고위험 문장들을 검색
        
        Args:
            embedding (List[float]): 검색할 쿼리 임베딩
            top_k (int): 반환할 최대 결과 수
            risk_score_threshold (float): 최소 위험 점수 임계값
            
        Returns:
            List[Dict[str, Any]]: 유사한 문장들의 리스트
                각 딕셔너리는 다음 키를 포함:
                - sentence: 문장 내용
                - user_id: 사용자 ID
                - post_id: 게시글 ID
                - risk_score: 위험 점수
                - similarity_score: 유사도 점수 (0.0~1.0)
                - created_at: 생성 시간
                - risk_factors: 위험 요소 리스트
        
        TODO: 실제 ChromaDB 검색 구현
        - 코사인 유사도 기반 벡터 검색
        - 메타데이터 필터링 (risk_score >= threshold)
        - 결과 정렬 및 제한
        """
        if not self.is_connected:
            print("[WARN] 벡터 DB에 연결되지 않음. 빈 결과를 반환합니다.")
            return []
            
        # 임시 구현 - 하드코딩된 더미 데이터 반환
        dummy_results = [
            {
                "sentence": "이 서비스 정말 싫어요. 그만두고 싶어요.",
                "user_id": "user001",
                "post_id": "post001", 
                "risk_score": 0.89,
                "similarity_score": 0.95,
                "created_at": datetime.now(),
                "risk_factors": ["고위험_키워드: 싫어", "고위험_키워드: 그만두고"]
            },
            {
                "sentence": "시간낭비인 것 같아서 포기할래요.",
                "user_id": "user002",
                "post_id": "post002",
                "risk_score": 0.82,
                "similarity_score": 0.87,
                "created_at": datetime.now(),
                "risk_factors": ["고위험_키워드: 시간낭비", "고위험_키워드: 포기"]
            },
            {
                "sentence": "너무 복잡해서 이해가 안돼요. 짜증나네요.",
                "user_id": "user003", 
                "post_id": "post003",
                "risk_score": 0.76,
                "similarity_score": 0.78,
                "created_at": datetime.now(),
                "risk_factors": ["중위험_키워드: 복잡해", "고위험_키워드: 짜증"]
            }
        ]
        
        # 임계값 필터링 및 상위 k개 반환
        filtered_results = [
            result for result in dummy_results 
            if result['risk_score'] >= risk_score_threshold
        ]
        
        return filtered_results[:top_k]
        
        # 실제 구현 예시:
        # results = self.collection.query(
        #     query_embeddings=[embedding],
        #     n_results=top_k,
        #     where={"risk_score": {"$gte": risk_score_threshold}}
        # )
        # return self._format_search_results(results)
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        컬렉션 통계 정보 조회
        
        Returns:
            Dict[str, Any]: 통계 정보
                - total_chunks: 총 저장된 문장 수
                - high_risk_count: 고위험 문장 수 (>= 0.75)
                - average_risk_score: 평균 위험 점수
                - latest_update: 최근 업데이트 시간
        
        TODO: 실제 ChromaDB 통계 조회 구현
        """
        if not self.is_connected:
            return {
                'total_chunks': 0,
                'high_risk_count': 0, 
                'average_risk_score': 0.0,
                'latest_update': None
            }
            
        # 임시 구현 - 더미 통계
        return {
            'total_chunks': 150,
            'high_risk_count': 45,
            'average_risk_score': 0.78,
            'latest_update': datetime.now()
        }
        
        # 실제 구현 예시:
        # count = self.collection.count()
        # all_metadata = self.collection.get()['metadatas']
        # high_risk_count = sum(1 for meta in all_metadata if meta.get('risk_score', 0) >= 0.75)
        # avg_score = sum(meta.get('risk_score', 0) for meta in all_metadata) / len(all_metadata)
        # return {...}
    
    def delete_old_chunks(self, days_old: int = 30) -> int:
        """
        오래된 문장 데이터 삭제
        
        Args:
            days_old (int): 삭제할 데이터의 기준 일수
            
        Returns:
            int: 삭제된 문장 수
            
        TODO: 실제 ChromaDB 삭제 구현
        - 날짜 기반 필터링
        - 배치 삭제 최적화
        """
        if not self.is_connected:
            return 0
            
        # 임시 구현
        print(f"[DEBUG] {days_old}일 이전 데이터 삭제 시뮬레이션")
        return 12  # 더미 삭제 개수
        
        # 실제 구현 예시:
        # cutoff_date = datetime.now() - timedelta(days=days_old)
        # old_ids = self.collection.get(
        #     where={"created_at": {"$lt": cutoff_date.isoformat()}}
        # )['ids']
        # if old_ids:
        #     self.collection.delete(ids=old_ids)
        # return len(old_ids)


# 전역 벡터 스토어 인스턴스 (싱글톤 패턴)
_vector_store_instance = None

def get_vector_store() -> VectorStore:
    """
    벡터 스토어 싱글톤 인스턴스 반환
    
    Returns:
        VectorStore: 벡터 스토어 인스턴스
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
        _vector_store_instance.connect()
    return _vector_store_instance


# 편의를 위한 함수형 인터페이스
def upsert_high_risk_chunk(embedding: List[float], metadata_dict: Dict[str, Any]) -> None:
    """
    고위험 문장을 벡터 DB에 저장하는 편의 함수
    
    Args:
        embedding (List[float]): 문장의 벡터 임베딩
        metadata_dict (Dict[str, Any]): 메타데이터
    """
    vector_store = get_vector_store()
    vector_store.upsert_high_risk_chunk(embedding, metadata_dict)


def search_similar_chunks(embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    유사한 고위험 문장들을 검색하는 편의 함수
    
    Args:
        embedding (List[float]): 검색할 쿼리 임베딩
        top_k (int): 반환할 최대 결과 수
        
    Returns:
        List[Dict[str, Any]]: 유사한 문장들의 리스트
    """
    vector_store = get_vector_store()
    return vector_store.search_similar_chunks(embedding, top_k)
