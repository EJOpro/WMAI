"""
BM25 검색 인덱스 저장소
rank-bm25를 사용하여 키워드 기반 검색을 제공합니다.
"""

import pickle
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
import kss


class BM25Store:
    """
    BM25 인덱스를 생성, 저장, 로드하고 검색하는 클래스
    """
    
    def __init__(self):
        """BM25Store 초기화"""
        self.bm25_index = None
        self.documents = []
        self.tokenized_corpus = []
    
    def create_bm25_index(self, documents: List[Document]) -> None:
        """
        Document 리스트로부터 BM25 인덱스 생성
        
        Args:
            documents: LangChain Document 객체 리스트
        """
        print(f"[BM25Store] BM25 인덱스 생성 중... (문서 {len(documents)}개)")
        
        self.documents = documents
        self.tokenized_corpus = []
        
        # 각 문서를 토큰화
        for doc in documents:
            # KSS로 문장 분리 후 공백으로 토큰화
            sentences = kss.split_sentences(doc.page_content)
            tokens = []
            for sentence in sentences:
                # 간단한 공백 기반 토큰화 (한국어에 적합하게 개선 가능)
                sentence_tokens = sentence.strip().split()
                tokens.extend(sentence_tokens)
            
            self.tokenized_corpus.append(tokens)
        
        # BM25 인덱스 생성
        self.bm25_index = BM25Okapi(self.tokenized_corpus)
        print(f"[BM25Store] BM25 인덱스 생성 완료")
    
    def save_index(self, file_path: str) -> None:
        """
        BM25 인덱스를 파일로 저장
        
        Args:
            file_path: 저장할 파일 경로 (.pkl)
        """
        if self.bm25_index is None:
            raise ValueError("BM25 인덱스가 생성되지 않았습니다. create_bm25_index()를 먼저 호출하세요.")
        
        # 저장할 데이터 준비
        save_data = {
            'bm25_index': self.bm25_index,
            'documents': self.documents,
            'tokenized_corpus': self.tokenized_corpus
        }
        
        # 디렉토리 생성
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 피클로 저장
        with open(file_path, 'wb') as f:
            pickle.dump(save_data, f)
        
        print(f"[BM25Store] 인덱스 저장 완료: {file_path}")
    
    @classmethod
    def load_index(cls, file_path: str) -> 'BM25Store':
        """
        저장된 BM25 인덱스를 로드
        
        Args:
            file_path: 로드할 파일 경로 (.pkl)
            
        Returns:
            로드된 BM25Store 인스턴스
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"BM25 인덱스 파일을 찾을 수 없습니다: {file_path}")
        
        # 피클에서 로드
        with open(file_path, 'rb') as f:
            save_data = pickle.load(f)
        
        # 인스턴스 생성 및 데이터 복원
        instance = cls()
        instance.bm25_index = save_data['bm25_index']
        instance.documents = save_data['documents']
        instance.tokenized_corpus = save_data['tokenized_corpus']
        
        print(f"[BM25Store] 인덱스 로드 완료: {file_path} (문서 {len(instance.documents)}개)")
        return instance
    
    def search(self, query: str, k: int = 10) -> List[Tuple[Document, float]]:
        """
        BM25 검색 수행
        
        Args:
            query: 검색 쿼리
            k: 반환할 상위 결과 개수
            
        Returns:
            (Document, score) 튜플 리스트 (점수 내림차순)
        """
        if self.bm25_index is None:
            raise ValueError("BM25 인덱스가 로드되지 않았습니다.")
        
        # 쿼리 토큰화
        query_sentences = kss.split_sentences(query)
        query_tokens = []
        for sentence in query_sentences:
            sentence_tokens = sentence.strip().split()
            query_tokens.extend(sentence_tokens)
        
        # BM25 점수 계산
        scores = self.bm25_index.get_scores(query_tokens)
        
        # 점수와 문서를 함께 정렬
        doc_scores = [(self.documents[i], scores[i]) for i in range(len(scores))]
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 k개 반환
        return doc_scores[:k]
    
    def as_retriever(self, k: int = 10) -> 'BM25Retriever':
        """
        LangChain Retriever 인터페이스로 변환
        
        Args:
            k: 검색 결과 개수
            
        Returns:
            BM25Retriever 인스턴스
        """
        return BM25Retriever(bm25_store=self, k=k)


class BM25Retriever(BaseRetriever):
    """
    BM25Store를 LangChain Retriever 인터페이스로 래핑
    """
    
    def __init__(self, bm25_store: BM25Store, k: int = 10):
        """
        Args:
            bm25_store: BM25Store 인스턴스
            k: 검색 결과 개수
        """
        super().__init__()
        self.bm25_store = bm25_store
        self.k = k
    
    def _get_relevant_documents(
        self, 
        query: str, 
        *, 
        run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """
        검색 쿼리에 대한 관련 문서 반환
        
        Args:
            query: 검색 쿼리
            run_manager: 콜백 매니저
            
        Returns:
            관련 Document 리스트
        """
        # BM25 검색 수행
        results = self.bm25_store.search(query, k=self.k)
        
        # Document만 추출하여 반환
        return [doc for doc, score in results]


def create_bm25_index_from_documents(
    documents: List[Document], 
    save_path: str = None
) -> BM25Store:
    """
    Document 리스트로부터 BM25 인덱스를 생성하는 헬퍼 함수
    
    Args:
        documents: Document 리스트
        save_path: 저장할 파일 경로 (None이면 저장하지 않음)
        
    Returns:
        BM25Store 인스턴스
    """
    store = BM25Store()
    store.create_bm25_index(documents)
    
    if save_path:
        store.save_index(save_path)
    
    return store


if __name__ == "__main__":
    # 테스트 코드
    print("=" * 60)
    print("BM25Store 테스트")
    print("=" * 60)
    
    # 테스트 문서 생성
    test_docs = [
        Document(
            page_content="인공지능 기술이 빠르게 발전하고 있습니다. 특히 자연어 처리 분야에서 놀라운 성과를 보이고 있죠.",
            metadata={"id": 1, "type": "board", "title": "AI 기술 동향"}
        ),
        Document(
            page_content="육아는 정말 힘든 일입니다. 하지만 아이와 함께하는 시간은 소중해요.",
            metadata={"id": 2, "type": "board", "title": "육아 이야기"}
        ),
        Document(
            page_content="요리 레시피를 공유합니다. 간단한 파스타 만드는 법을 알려드릴게요.",
            metadata={"id": 3, "type": "board", "title": "요리 레시피"}
        )
    ]
    
    # BM25 인덱스 생성
    store = BM25Store()
    store.create_bm25_index(test_docs)
    
    # 검색 테스트
    print("\n'육아' 검색 결과:")
    results = store.search("육아", k=2)
    for idx, (doc, score) in enumerate(results, 1):
        print(f"  {idx}. 점수: {score:.3f}")
        print(f"     제목: {doc.metadata.get('title', '제목 없음')}")
        print(f"     내용: {doc.page_content[:50]}...")
    
    # 저장/로드 테스트
    test_path = "test_bm25_index.pkl"
    store.save_index(test_path)
    
    loaded_store = BM25Store.load_index(test_path)
    print(f"\n로드된 인덱스로 '요리' 검색:")
    results = loaded_store.search("요리", k=2)
    for idx, (doc, score) in enumerate(results, 1):
        print(f"  {idx}. 점수: {score:.3f}")
        print(f"     제목: {doc.metadata.get('title', '제목 없음')}")
    
    # 테스트 파일 삭제
    if os.path.exists(test_path):
        os.remove(test_path)
    
    print("\n[OK] BM25Store 테스트 완료!")
