"""
벡터 스토어 모듈
고위험 문장들을 벡터 데이터베이스에 저장하고 검색하는 기능을 제공합니다.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime, timedelta
from .vector_db import get_client, get_collection, upsert_confirmed_chunk, search_similar, build_chunk_id


class VectorStore:
    """
    벡터 데이터베이스 인터페이스 클래스
    ChromaDB를 사용하여 고위험 문장들을 저장하고 검색합니다.
    """
    
    def __init__(self, collection_name: str = "high_risk_sentences"):
        """
        벡터 스토어 초기화
        
        Args:
            collection_name (str): 컬렉션 이름
        """
        self.collection_name = collection_name
        self.is_connected = False
        self.client = None
        self.collection = None
        
    def connect(self) -> bool:
        """
        벡터 데이터베이스에 연결
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            self.client = get_client()
            self.collection = get_collection(self.client, self.collection_name)
            self.is_connected = True
            print(f"[INFO] VectorStore 연결 성공: {self.collection_name}")
            return True
        except Exception as e:
            print(f"[ERROR] VectorStore 연결 실패: {e}")
            self.is_connected = False
            return False
        
    def disconnect(self) -> None:
        """
        벡터 데이터베이스 연결 해제
        """
        self.client = None
        self.collection = None
        self.is_connected = False
        print(f"[INFO] VectorStore 연결 해제: {self.collection_name}")
        
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
        """
        if not self.is_connected:
            print("[WARN] 벡터 DB에 연결되지 않음. 연결을 먼저 수행하세요.")
            return
            
        try:
            # chunk_id 생성
            sentence = metadata_dict.get('sentence', '')
            post_id = metadata_dict.get('post_id', '')
            chunk_id = build_chunk_id(sentence, post_id)
            
            # 메타데이터에 chunk_id 추가
            metadata_dict['chunk_id'] = chunk_id
            
            # ChromaDB에 저장
            upsert_confirmed_chunk(self.client, embedding, metadata_dict, self.collection_name)
            
            print(f"[INFO] 고위험 문장 저장 완료: {sentence[:50]}... (위험점수: {metadata_dict.get('risk_score', 0.0)})")
            
        except Exception as e:
            print(f"[ERROR] 고위험 문장 저장 실패: {e}")
            import traceback
            traceback.print_exc()
        
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
        """
        if not self.is_connected:
            print("[WARN] 벡터 DB에 연결되지 않음. 빈 결과를 반환합니다.")
            return []
            
        try:
            # ChromaDB에서 유사 문장 검색
            similar_results = search_similar(
                client=self.client,
                embedding=embedding,
                top_k=top_k,
                min_score=1.0 - risk_score_threshold,  # 거리를 유사도로 변환
                collection_name=self.collection_name
            )
            
            # 결과 포맷팅
            formatted_results = []
            for result in similar_results:
                metadata = result.get('metadata', {})
                
                # risk_score 필터링
                risk_score = float(metadata.get('risk_score', 0.0))
                if risk_score >= risk_score_threshold:
                    formatted_result = {
                        "sentence": result.get('document', ''),
                        "user_id": metadata.get('user_id', ''),
                        "post_id": metadata.get('post_id', ''),
                        "risk_score": risk_score,
                        "similarity_score": float(result.get('score', 0.0)),
                        "created_at": metadata.get('created_at', ''),
                        "risk_factors": metadata.get('risk_factors', []),
                        "chunk_id": result.get('id', '')
                    }
                    formatted_results.append(formatted_result)
            
            print(f"[INFO] 유사 문장 검색 완료: {len(formatted_results)}개 발견")
            return formatted_results
            
        except Exception as e:
            print(f"[ERROR] 유사 문장 검색 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        컬렉션 통계 정보 조회
        
        Returns:
            Dict[str, Any]: 통계 정보
        """
        if not self.is_connected:
            return {
                'total_chunks': 0,
                'high_risk_count': 0, 
                'average_risk_score': 0.0,
                'latest_update': None,
                'status': 'disconnected'
            }
            
        try:
            # ChromaDB에서 통계 조회
            from .vector_db import get_collection_stats
            stats = get_collection_stats(self.client, self.collection_name)
            
            # 추가 통계 계산
            if stats.get('total_documents', 0) > 0:
                # 모든 메타데이터 조회
                all_data = self.collection.get(include=['metadatas'])
                metadatas = all_data.get('metadatas', [])
                
                if metadatas:
                    # 고위험 문장 수 계산
                    high_risk_count = sum(1 for meta in metadatas if float(meta.get('risk_score', 0)) >= 0.75)
                    
                    # 평균 위험 점수 계산
                    risk_scores = [float(meta.get('risk_score', 0)) for meta in metadatas]
                    avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
                    
                    # 최근 업데이트 시간
                    created_dates = [meta.get('created_at') for meta in metadatas if meta.get('created_at')]
                    latest_update = max(created_dates) if created_dates else None
                    
                    stats.update({
                        'high_risk_count': high_risk_count,
                        'average_risk_score': round(avg_risk_score, 3),
                        'latest_update': latest_update
                    })
            
            return stats
            
        except Exception as e:
            print(f"[ERROR] 컬렉션 통계 조회 실패: {e}")
            return {
                'total_chunks': 0,
                'high_risk_count': 0,
                'average_risk_score': 0.0,
                'latest_update': None,
                'status': 'error',
                'error': str(e)
            }
    
    def delete_old_chunks(self, days_old: int = 30) -> int:
        """
        오래된 문장 데이터 삭제
        
        Args:
            days_old (int): 삭제할 데이터의 기준 일수
            
        Returns:
            int: 삭제된 문장 수
        """
        if not self.is_connected:
            return 0
            
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat()
            
            # 오래된 데이터 조회
            all_data = self.collection.get(include=['metadatas'])
            old_ids = []
            
            for i, metadata in enumerate(all_data.get('metadatas', [])):
                created_at = metadata.get('created_at', '')
                if created_at and created_at < cutoff_str:
                    old_ids.append(all_data['ids'][i])
            
            # 삭제 실행
            if old_ids:
                from .vector_db import delete_chunk
                deleted_count = 0
                for chunk_id in old_ids:
                    if delete_chunk(self.client, chunk_id, self.collection_name):
                        deleted_count += 1
                
                print(f"[INFO] {deleted_count}개의 오래된 문장 삭제 완료 ({days_old}일 이전)")
                return deleted_count
            else:
                print(f"[INFO] 삭제할 오래된 문장이 없습니다 ({days_old}일 이전)")
                return 0
                
        except Exception as e:
            print(f"[ERROR] 오래된 문장 삭제 실패: {e}")
            return 0


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
