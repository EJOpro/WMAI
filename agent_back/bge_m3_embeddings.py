"""
BGE-M3 임베딩 모델을 로컬에서 직접 사용하는 LangChain Embeddings 클래스

BGE-M3는 다국어 임베딩 모델로 한국어를 포함한 100개 이상의 언어를 지원합니다.
- 모델: BAAI/bge-m3
- 임베딩 차원: 1024
- 최대 토큰 길이: 8192
- 로컬 실행: API 키 불필요, 무제한 사용
"""

from typing import List
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


class BGEM3Embeddings(Embeddings):
    """
    BGE-M3 임베딩을 로컬에서 생성하는 클래스
    
    장점:
    - API 키 불필요
    - Rate limit 없음
    - 더 빠른 속도 (GPU 사용 시)
    - 오프라인 사용 가능
    """
    
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = None):
        """
        Args:
            model_name: 사용할 모델 이름 (기본값: BAAI/bge-m3)
            device: 실행 장치 ('cuda', 'cpu', None=자동)
                   None이면 GPU가 있으면 자동으로 GPU 사용
        """
        print(f"BGE-M3 모델 로딩 중: {model_name}")
        print("최초 실행 시 모델 다운로드 (약 2GB, 1~2분 소요)...")
        
        self.model = SentenceTransformer(model_name, device=device)
        
        print(f"[OK] BGE-M3 모델 로딩 완료! (장치: {self.model.device})")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        문서 리스트를 임베딩으로 변환 (LangChain 인터페이스)
        
        Args:
            texts: 임베딩할 문서 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        # sentence-transformers의 encode 메서드 사용
        # convert_to_numpy=False로 설정하여 리스트로 반환
        embeddings = self.model.encode(
            texts,
            convert_to_tensor=False,
            normalize_embeddings=True,  # 코사인 유사도를 위한 정규화
            show_progress_bar=len(texts) > 50  # 50개 이상일 때만 진행 표시
        )
        
        # numpy array를 리스트로 변환
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """
        단일 쿼리 텍스트를 임베딩으로 변환 (LangChain 인터페이스)
        
        Args:
            text: 임베딩할 쿼리 텍스트
            
        Returns:
            임베딩 벡터
        """
        embedding = self.model.encode(
            text,
            convert_to_tensor=False,
            normalize_embeddings=True
        )
        
        # numpy array를 리스트로 변환
        return embedding.tolist()


