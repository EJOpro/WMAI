"""
벡터 스토어 모듈
고위험 문장들을 벡터 데이터베이스에 저장하고 검색하는 기능을 제공합니다.
FAISS와 ChromaDB 어댑터를 지원합니다.
"""

import os
from typing import List, Dict, Any, Optional, Protocol
import numpy as np
from datetime import datetime, timedelta
from .vector_db import get_client, get_collection, upsert_confirmed_chunk, search_similar, build_chunk_id
from .privacy_utils import sanitize_metadata
from .embedding_service import EMBEDDING_MODEL, EMBEDDING_DIMENSION


class VectorStoreAdapter(Protocol):
    """벡터 스토어 어댑터 프로토콜"""
    def upsert(self, embedding: List[float], metadata: Dict[str, Any]) -> None:
        ...
    def search(self, embedding: List[float], top_k: int, min_score: float) -> List[Dict[str, Any]]:
        ...
    def get_stats(self) -> Dict[str, Any]:
        ...


class ChromaDBAdapter:
    """ChromaDB 어댑터"""
    def __init__(self, collection_name: str = "high_risk_sentences"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.is_connected = False
    
    def connect(self) -> bool:
        try:
            self.client = get_client()
            self.collection = get_collection(self.client, self.collection_name)
            self.is_connected = True
            return True
        except Exception as e:
            print(f"[ERROR] ChromaDB 연결 실패: {e}")
            self.is_connected = False
            return False
    
    def upsert(self, embedding: List[float], metadata: Dict[str, Any]) -> None:
        if not self.is_connected:
            raise RuntimeError("ChromaDB에 연결되지 않음")
        upsert_confirmed_chunk(self.client, embedding, metadata, self.collection_name)
    
    def search(self, embedding: List[float], top_k: int, min_score: float) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        return search_similar(self.client, embedding, top_k, min_score, self.collection_name)
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.is_connected:
            return {'total_documents': 0, 'status': 'disconnected'}
        try:
            from .vector_db import get_collection_stats
            return get_collection_stats(self.client, self.collection_name)
        except Exception as e:
            return {'total_documents': 0, 'status': 'error', 'error': str(e)}


class FAISSAdapter:
    """FAISS 어댑터"""
    def __init__(self, index_path: str = "./faiss_index", dimension: int = EMBEDDING_DIMENSION):
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.metadata_store = {}  # chunk_id -> metadata 매핑
        self.id_to_index = {}  # chunk_id -> index 위치 매핑
        self.index_to_id = {}  # index 위치 -> chunk_id 매핑
        self.id_counter = 0
        self.is_connected = False
    
    def connect(self) -> bool:
        try:
            import faiss
            os.makedirs(os.path.dirname(self.index_path) if os.path.dirname(self.index_path) else '.', exist_ok=True)
            
            # 인덱스 파일이 있으면 로드, 없으면 새로 생성
            if os.path.exists(f"{self.index_path}.index"):
                self.index = faiss.read_index(f"{self.index_path}.index")
                # 메타데이터도 로드
                import json
                if os.path.exists(f"{self.index_path}.meta"):
                    with open(f"{self.index_path}.meta", 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.metadata_store = data.get('metadata', {})
                        self.id_to_index = data.get('id_to_index', {})
                        self.index_to_id = data.get('index_to_id', {})
                        self.id_counter = data.get('id_counter', 0)
            else:
                # L2 거리 기반 인덱스 생성
                self.index = faiss.IndexFlatL2(self.dimension)
            
            self.is_connected = True
            return True
        except ImportError:
            print("[WARN] FAISS가 설치되지 않았습니다. pip install faiss-cpu 실행 필요")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"[ERROR] FAISS 연결 실패: {e}")
            self.is_connected = False
            return False
    
    def upsert(self, embedding: List[float], metadata: Dict[str, Any]) -> None:
        if not self.is_connected:
            raise RuntimeError("FAISS에 연결되지 않음")
        
        import faiss
        import json
        
        chunk_id = metadata.get('chunk_id', f"chunk_{self.id_counter}")
        
        # 기존 ID가 있으면 메타데이터만 업데이트
        if chunk_id in self.metadata_store:
            # 기존 메타데이터 업데이트
            self.metadata_store[chunk_id].update(metadata)
            # 벡터는 업데이트하지 않음 (FAISS는 삭제를 직접 지원하지 않음)
            # 실제 운영 환경에서는 벡터 재생성 또는 별도 관리 권장
        else:
            # 새 항목 추가
            vector = np.array([embedding], dtype=np.float32)
            index_pos = self.index.ntotal  # 현재 인덱스 위치
            self.index.add(vector)
            
            # ID 매핑 저장
            self.metadata_store[chunk_id] = metadata
            self.id_to_index[chunk_id] = index_pos
            self.index_to_id[index_pos] = chunk_id
            self.id_counter += 1
        
        # 디스크에 저장
        faiss.write_index(self.index, f"{self.index_path}.index")
        with open(f"{self.index_path}.meta", 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': self.metadata_store,
                'id_to_index': self.id_to_index,
                'index_to_id': self.index_to_id,
                'id_counter': self.id_counter
            }, f, ensure_ascii=False, indent=2)
    
    def search(self, embedding: List[float], top_k: int, min_score: float) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
        
        import numpy as np
        
        # 벡터를 numpy 배열로 변환
        query_vector = np.array([embedding], dtype=np.float32)
        
        # 검색 (L2 거리)
        distances, indices = self.index.search(query_vector, top_k)
        
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < 0:  # FAISS는 -1을 반환할 수 있음
                continue
            
            # 거리를 유사도로 변환 (1 / (1 + distance))
            similarity = 1.0 / (1.0 + distance)
            
            if similarity >= min_score:
                # 인덱스 위치로부터 chunk_id 조회
                chunk_id = self.index_to_id.get(idx, f"chunk_{idx}")
                metadata = self.metadata_store.get(chunk_id, {})
                
                results.append({
                    'id': chunk_id,
                    'score': similarity,
                    'metadata': metadata,
                    'document': metadata.get('sentence', '')
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.is_connected:
            return {'total_documents': 0, 'status': 'disconnected'}
        return {
            'total_documents': self.index.ntotal if self.index else 0,
            'status': 'connected',
            'dimension': self.dimension
        }


class VectorStore:
    """
    벡터 데이터베이스 인터페이스 클래스
    FAISS와 ChromaDB 어댑터를 지원합니다.
    """
    
    def __init__(self, collection_name: str = "high_risk_sentences", backend: str = "chroma"):
        """
        벡터 스토어 초기화
        
        Args:
            collection_name (str): 컬렉션 이름
            backend (str): 백엔드 타입 ("chroma" 또는 "faiss")
        """
        self.collection_name = collection_name
        self.backend_type = backend.lower()
        self.adapter: Optional[VectorStoreAdapter] = None
        self.is_connected = False
        
        # 백엔드별 어댑터 생성
        if self.backend_type == "faiss":
            self.adapter = FAISSAdapter(index_path=f"./faiss_index_{collection_name}")
        else:  # 기본값: chroma
            self.adapter = ChromaDBAdapter(collection_name=collection_name)
        
    def connect(self) -> bool:
        """
        벡터 데이터베이스에 연결
        
        Returns:
            bool: 연결 성공 여부
        """
        if not self.adapter:
            return False
        
        if isinstance(self.adapter, ChromaDBAdapter):
            self.is_connected = self.adapter.connect()
        elif isinstance(self.adapter, FAISSAdapter):
            self.is_connected = self.adapter.connect()
        else:
            self.is_connected = False
        
        if self.is_connected:
            print(f"[INFO] VectorStore 연결 성공: {self.backend_type} ({self.collection_name})")
        else:
            print(f"[ERROR] VectorStore 연결 실패: {self.backend_type}")
        
        return self.is_connected
        
    def disconnect(self) -> None:
        """
        벡터 데이터베이스 연결 해제
        """
        self.adapter = None
        self.is_connected = False
        print(f"[INFO] VectorStore 연결 해제: {self.collection_name}")
        
    def upsert_high_risk_chunk(
        self, 
        embedding: List[float], 
        metadata_dict: Dict[str, Any],
        confirmed: bool = False,
        who_labeled: Optional[str] = None,
        segment: Optional[str] = None,
        reason: Optional[str] = None
    ) -> None:
        """
        고위험 문장의 임베딩과 메타데이터를 벡터 DB에 저장
        
        Args:
            embedding (List[float]): 문장의 벡터 임베딩
            metadata_dict (Dict[str, Any]): 메타데이터
            confirmed (bool): 확정 여부 (기본값: False)
            who_labeled (str, optional): 라벨링한 사용자/시스템
            segment (str, optional): 세그먼트 정보
            reason (str, optional): 확정 이유
        """
        if not self.is_connected or not self.adapter:
            print("[WARN] 벡터 DB에 연결되지 않음. 연결을 먼저 수행하세요.")
            return
            
        try:
            # chunk_id 생성
            sentence = metadata_dict.get('sentence', '')
            post_id = metadata_dict.get('post_id', '')
            chunk_id = build_chunk_id(sentence, post_id)
            
            # 개인정보 마스킹
            sanitized_metadata = sanitize_metadata(metadata_dict.copy())
            
            # 메타데이터 구성
            final_metadata = {
                **sanitized_metadata,
                'chunk_id': chunk_id,
                'confirmed': confirmed,
                'embed_model_v': EMBEDDING_MODEL,  # 임베딩 모델 버전
                'embed_dimension': EMBEDDING_DIMENSION,  # 임베딩 차원
                'ts': datetime.now().isoformat(),  # 타임스탬프
            }
            
            # 확정 관련 메타데이터 추가
            if who_labeled:
                final_metadata['who_labeled'] = who_labeled
            if segment:
                final_metadata['segment'] = segment
            if reason:
                final_metadata['reason'] = reason
            
            # 어댑터를 통해 저장
            self.adapter.upsert(embedding, final_metadata)
            
            print(f"[INFO] 고위험 문장 저장 완료: {sentence[:50]}... (위험점수: {final_metadata.get('risk_score', 0.0)}, 확정: {confirmed})")
            
        except Exception as e:
            print(f"[ERROR] 고위험 문장 저장 실패: {e}")
            import traceback
            traceback.print_exc()
        
    def search_similar_chunks(
        self, 
        embedding: List[float], 
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        confirmed_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        주어진 임베딩과 유사한 고위험 문장들을 Top-k 검색
        
        Args:
            embedding (List[float]): 검색할 쿼리 임베딩
            top_k (int): 반환할 최대 결과 수
            similarity_threshold (float): 최소 유사도 임계값 (0.0~1.0)
            confirmed_only (bool): confirmed=true인 항목만 검색
            
        Returns:
            List[Dict[str, Any]]: 유사한 문장들의 리스트
        """
        if not self.is_connected or not self.adapter:
            print("[WARN] 벡터 DB에 연결되지 않음. 빈 결과를 반환합니다.")
            return []
            
        try:
            # 어댑터를 통해 Top-k 검색
            min_score = similarity_threshold
            similar_results = self.adapter.search(embedding, top_k, min_score)
            
            # 결과 포맷팅
            formatted_results = []
            for result in similar_results:
                metadata = result.get('metadata', {})
                
                # confirmed 필터링
                if confirmed_only and not metadata.get('confirmed', False):
                    continue
                
                formatted_result = {
                    "sentence": result.get('document', ''),
                    "user_id": metadata.get('user_id', ''),
                    "post_id": metadata.get('post_id', ''),
                    "risk_score": float(metadata.get('risk_score', 0.0)),
                    "similarity_score": float(result.get('score', 0.0)),
                    "created_at": metadata.get('created_at', ''),
                    "risk_factors": metadata.get('risk_factors', []),
                    "chunk_id": result.get('id', ''),
                    "confirmed": metadata.get('confirmed', False),
                    "segment": metadata.get('segment'),
                    "reason": metadata.get('reason')
                }
                formatted_results.append(formatted_result)
            
            print(f"[INFO] 유사 문장 검색 완료: {len(formatted_results)}개 발견 (Top-{top_k})")
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
        if not self.is_connected or not self.adapter:
            return {
                'total_chunks': 0,
                'high_risk_count': 0, 
                'average_risk_score': 0.0,
                'latest_update': None,
                'status': 'disconnected',
                'backend': self.backend_type
            }
            
        try:
            stats = self.adapter.get_stats()
            stats['backend'] = self.backend_type
            stats['embed_model'] = EMBEDDING_MODEL
            stats['embed_dimension'] = EMBEDDING_DIMENSION
            return stats
            
        except Exception as e:
            print(f"[ERROR] 컬렉션 통계 조회 실패: {e}")
            return {
                'total_chunks': 0,
                'high_risk_count': 0,
                'average_risk_score': 0.0,
                'latest_update': None,
                'status': 'error',
                'error': str(e),
                'backend': self.backend_type
            }
    
    def delete_old_chunks(self, days_old: int = 30) -> int:
        """
        오래된 문장 데이터 삭제 (ChromaDB만 지원)
        
        Args:
            days_old (int): 삭제할 데이터의 기준 일수
            
        Returns:
            int: 삭제된 문장 수
        """
        if not self.is_connected or not isinstance(self.adapter, ChromaDBAdapter):
            print("[WARN] 삭제 기능은 ChromaDB에서만 지원됩니다.")
            return 0
            
        try:
            from .vector_db import delete_chunk
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_str = cutoff_date.isoformat()
            
            # 오래된 데이터 조회
            all_data = self.adapter.collection.get(include=['metadatas', 'ids'])
            old_ids = []
            
            for i, metadata in enumerate(all_data.get('metadatas', [])):
                created_at = metadata.get('created_at', '')
                if created_at and created_at < cutoff_str:
                    old_ids.append(all_data['ids'][i])
            
            # 삭제 실행
            if old_ids:
                deleted_count = 0
                for chunk_id in old_ids:
                    if delete_chunk(self.adapter.client, chunk_id, self.collection_name):
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

def get_vector_store(backend: str = "chroma") -> VectorStore:
    """
    벡터 스토어 싱글톤 인스턴스 반환
    
    Args:
        backend (str): 백엔드 타입 ("chroma" 또는 "faiss")
    
    Returns:
        VectorStore: 벡터 스토어 인스턴스
    """
    global _vector_store_instance
    backend_env = os.getenv("VECTOR_STORE_BACKEND", backend)
    if _vector_store_instance is None or _vector_store_instance.backend_type != backend_env:
        _vector_store_instance = VectorStore(backend=backend_env)
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


def search_similar_chunks(
    embedding: List[float], 
    top_k: int = 5,
    similarity_threshold: float = 0.7,
    confirmed_only: bool = False
) -> List[Dict[str, Any]]:
    """
    유사한 고위험 문장들을 검색하는 편의 함수
    
    Args:
        embedding (List[float]): 검색할 쿼리 임베딩
        top_k (int): 반환할 최대 결과 수
        similarity_threshold (float): 최소 유사도 임계값
        confirmed_only (bool): confirmed=true인 항목만 검색
        
    Returns:
        List[Dict[str, Any]]: 유사한 문장들의 리스트
    """
    vector_store = get_vector_store()
    return vector_store.search_similar_chunks(embedding, top_k, similarity_threshold, confirmed_only)
