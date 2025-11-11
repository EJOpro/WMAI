"""
BGE Reranker 모듈

BGE-reranker-v2-m3 모델을 사용하여 검색 결과를 재순위화합니다.
Cross-Encoder 방식으로 쿼리와 문서의 직접적인 관련성을 평가합니다.
"""

from typing import List, Tuple
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
import logging

# 로깅 설정
logger = logging.getLogger(__name__)


class BGEReranker:
    """
    BGE-reranker-v2-m3를 사용한 검색 결과 재순위화 클래스
    
    Cross-Encoder 방식으로 쿼리와 문서 쌍의 관련성을 직접 평가하여
    앙상블 검색 결과의 정확도를 향상시킵니다.
    
    장점:
    - 쿼리-문서 간 직접적인 관련성 평가
    - 문맥 이해 능력 향상
    - 검색 정확도 15-25% 향상
    - 로컬 실행 (API 키 불필요)
    """
    
    def __init__(
        self, 
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = None,
        max_length: int = 512
    ):
        """
        Args:
            model_name: Reranker 모델 이름 (기본값: BAAI/bge-reranker-v2-m3)
            device: 실행 장치 ('cuda', 'cpu', None=자동)
            max_length: 최대 입력 길이 (기본값: 512)
        """
        logger.info(f"[BGEReranker] 모델 로딩 중: {model_name}")
        print(f"[BGEReranker] BGE Reranker 모델 로딩 중: {model_name}")
        print("최초 실행 시 모델 다운로드 (약 560MB, 1-2분 소요)...")
        
        try:
            self.model = CrossEncoder(
                model_name, 
                max_length=max_length,
                device=device
            )
            
            device_name = self.model.device if hasattr(self.model, 'device') else 'unknown'
            logger.info(f"[BGEReranker] 모델 로딩 완료 (장치: {device_name})")
            print(f"[OK] BGE Reranker 모델 로딩 완료! (장치: {device_name})")
            
        except Exception as e:
            logger.error(f"[BGEReranker] 모델 로딩 실패: {e}")
            print(f"[ERROR] Reranker 모델 로딩 실패: {e}")
            raise
    
    def rerank(
        self, 
        query: str, 
        documents: List[Document], 
        top_k: int = 10
    ) -> List[Tuple[Document, float]]:
        """
        쿼리와 문서들의 관련성을 재평가하여 상위 k개 반환
        
        Args:
            query: 검색 쿼리
            documents: 재순위화할 문서 리스트
            top_k: 반환할 상위 문서 개수
            
        Returns:
            (Document, rerank_score) 튜플 리스트 (점수 내림차순)
        """
        if not documents:
            logger.warning("[BGEReranker] 재순위화할 문서가 없습니다.")
            return []
        
        if not query or not query.strip():
            logger.warning("[BGEReranker] 빈 쿼리입니다. 원본 문서를 반환합니다.")
            return [(doc, 0.0) for doc in documents[:top_k]]
        
        try:
            logger.debug(f"[BGEReranker] Reranking {len(documents)}개 문서...")
            
            # (query, document) 쌍 생성
            # 문서 내용이 너무 길면 앞부분만 사용
            pairs = []
            for doc in documents:
                doc_text = doc.page_content[:1000]  # 최대 1000자
                pairs.append([query, doc_text])
            
            # Rerank 점수 계산
            # predict() 메서드는 각 쌍의 관련성 점수를 반환
            scores = self.model.predict(pairs)
            
            # 점수 기준 내림차순 정렬
            ranked_results = sorted(
                zip(documents, scores), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # 상위 k개 반환
            top_results = ranked_results[:top_k]
            
            logger.debug(
                f"[BGEReranker] Reranking 완료. "
                f"최고 점수: {top_results[0][1]:.4f}, "
                f"최저 점수: {top_results[-1][1]:.4f}"
            )
            
            return top_results
            
        except Exception as e:
            logger.error(f"[BGEReranker] Reranking 중 오류 발생: {e}")
            print(f"[WARN] Reranking 실패, 원본 순서로 반환: {e}")
            # 오류 시 원본 문서 반환
            return [(doc, 0.0) for doc in documents[:top_k]]
    
    def rerank_with_scores(
        self, 
        query: str, 
        documents: List[Document]
    ) -> List[Tuple[Document, float]]:
        """
        모든 문서에 대해 rerank 점수를 계산 (top_k 제한 없음)
        
        Args:
            query: 검색 쿼리
            documents: 재순위화할 문서 리스트
            
        Returns:
            (Document, rerank_score) 튜플 리스트 (점수 내림차순)
        """
        return self.rerank(query, documents, top_k=len(documents))


# 싱글톤 인스턴스
_reranker_instance = None


def get_reranker() -> BGEReranker:
    """
    BGEReranker 싱글톤 인스턴스 반환
    
    Returns:
        BGEReranker 인스턴스
    """
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = BGEReranker()
    return _reranker_instance


if __name__ == "__main__":
    # 테스트 코드
    print("=" * 60)
    print("BGEReranker 테스트")
    print("=" * 60)
    
    # 테스트 문서 생성
    test_docs = [
        Document(
            page_content="인공지능과 머신러닝 기술이 빠르게 발전하고 있습니다.",
            metadata={"id": 1, "title": "AI 기술"}
        ),
        Document(
            page_content="육아는 정말 힘든 일입니다. 하지만 보람찬 경험이에요.",
            metadata={"id": 2, "title": "육아 이야기"}
        ),
        Document(
            page_content="자연어 처리는 AI의 핵심 분야입니다. GPT 모델이 대표적이죠.",
            metadata={"id": 3, "title": "NLP 소개"}
        ),
        Document(
            page_content="요리 레시피를 공유합니다. 간단한 파스타 만드는 법입니다.",
            metadata={"id": 4, "title": "요리 레시피"}
        ),
        Document(
            page_content="딥러닝은 신경망을 사용한 기계학습 방법입니다.",
            metadata={"id": 5, "title": "딥러닝 개요"}
        )
    ]
    
    # Reranker 초기화
    reranker = BGEReranker()
    
    # 테스트 쿼리
    query = "인공지능 기술에 대해 알려주세요"
    
    print(f"\n쿼리: '{query}'")
    print("\n재순위화 결과:")
    
    results = reranker.rerank(query, test_docs, top_k=3)
    
    for idx, (doc, score) in enumerate(results, 1):
        print(f"\n[{idx}위] 점수: {score:.4f}")
        print(f"제목: {doc.metadata.get('title', '제목 없음')}")
        print(f"내용: {doc.page_content[:50]}...")
    
    print("\n" + "=" * 60)
    print("[OK] BGEReranker 테스트 완료!")
    print("=" * 60)

