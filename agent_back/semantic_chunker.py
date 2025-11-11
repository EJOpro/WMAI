"""
의미 기반 텍스트 청킹 모듈

KSS(Korean Sentence Splitter)로 문장을 분리하고,
SBERT(BGE-M3) 임베딩의 코사인 유사도를 기반으로
의미적으로 연관된 문장들을 청크로 그룹화합니다.
"""

from typing import List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import kss


class SemanticChunker:
    """
    의미 기반 텍스트 청킹 클래스
    
    KSS로 문장을 분리한 후, 문장 간 의미적 유사도를 계산하여
    유사도가 높은 연속된 문장들을 하나의 청크로 묶습니다.
    """
    
    def __init__(
        self, 
        model_name: str = "BAAI/bge-m3",
        similarity_threshold: float = 0.75,
        min_chunk_size: int = 80,
        max_chunk_size: int = 1200,
        device: str = None
    ):
        """
        Args:
            model_name: 임베딩 모델 이름 (기본값: BAAI/bge-m3)
            similarity_threshold: 청크 병합을 위한 유사도 임계값 (0~1, 기본값: 0.75)
            min_chunk_size: 최소 청크 크기 (글자 수, 기본값: 80)
            max_chunk_size: 최대 청크 크기 (글자 수, 기본값: 1200)
            device: 실행 장치 ('cuda', 'cpu', None=자동)
        """
        print(f"[SemanticChunker] BGE-M3 모델 로딩 중: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        print(f"[SemanticChunker] 초기화 완료 (임계값: {similarity_threshold}, 장치: {self.model.device})")
    
    def chunk_text(self, text: str) -> List[str]:
        """
        텍스트를 의미 기반으로 청크 분할
        
        Args:
            text: 분할할 텍스트
            
        Returns:
            청크 리스트
        """
        if not text or not text.strip():
            return []
        
        # 1. KSS로 문장 분리
        sentences = kss.split_sentences(text)
        
        # 빈 문장 제거 및 공백 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return []
        
        # 문장이 하나뿐이면 그대로 반환
        if len(sentences) == 1:
            return sentences
        
        # 2. 문장별 임베딩 생성
        embeddings = self.model.encode(
            sentences,
            convert_to_tensor=False,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        
        # 3. 유사도 기반 청킹
        chunks = self._group_by_similarity(sentences, embeddings)
        
        return chunks
    
    def _group_by_similarity(
        self, 
        sentences: List[str], 
        embeddings: np.ndarray
    ) -> List[str]:
        """
        문장 임베딩의 유사도를 기반으로 청크 그룹화
        
        Args:
            sentences: 문장 리스트
            embeddings: 문장 임베딩 배열
            
        Returns:
            청크 리스트
        """
        if len(sentences) == 0:
            return []
        
        if len(sentences) == 1:
            return sentences
        
        # 연속된 문장 간의 유사도 계산
        similarities = []
        for i in range(len(sentences) - 1):
            sim = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[i + 1].reshape(1, -1)
            )[0][0]
            similarities.append(sim)
        
        # 청크 경계 결정
        chunks = []
        current_chunk = [sentences[0]]
        current_chunk_size = len(sentences[0])
        
        for i in range(len(similarities)):
            next_sentence = sentences[i + 1]
            next_sentence_size = len(next_sentence)
            similarity = similarities[i]
            
            # 청크 병합 조건:
            # 1) 유사도가 임계값 이상
            # 2) 최대 청크 크기를 초과하지 않음
            should_merge = (
                similarity >= self.similarity_threshold and
                current_chunk_size + next_sentence_size <= self.max_chunk_size
            )
            
            if should_merge:
                # 현재 청크에 추가
                current_chunk.append(next_sentence)
                current_chunk_size += next_sentence_size
            else:
                # 현재 청크를 완성하고 새 청크 시작
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                current_chunk = [next_sentence]
                current_chunk_size = next_sentence_size
        
        # 마지막 청크 추가
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)
        
        # 너무 작은 청크는 이전 청크와 병합
        chunks = self._merge_small_chunks(chunks)
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """
        최소 크기보다 작은 청크를 이전 청크와 병합
        
        Args:
            chunks: 청크 리스트
            
        Returns:
            병합된 청크 리스트
        """
        if not chunks:
            return []
        
        merged = [chunks[0]]
        
        for chunk in chunks[1:]:
            # 현재 청크가 최소 크기보다 작으면 이전 청크와 병합
            if len(chunk) < self.min_chunk_size:
                # 병합해도 최대 크기를 초과하지 않는지 확인
                if len(merged[-1]) + len(chunk) <= self.max_chunk_size:
                    merged[-1] = merged[-1] + ' ' + chunk
                else:
                    # 최대 크기를 초과하면 별도 청크로 유지
                    merged.append(chunk)
            else:
                merged.append(chunk)
        
        return merged
    
    def chunk_text_with_metadata(
        self, 
        text: str, 
        metadata: dict = None
    ) -> List[Tuple[str, dict]]:
        """
        텍스트를 청크로 분할하고 메타데이터 포함
        
        Args:
            text: 분할할 텍스트
            metadata: 청크에 포함할 메타데이터
            
        Returns:
            (청크, 메타데이터) 튜플 리스트
        """
        chunks = self.chunk_text(text)
        
        result = []
        for idx, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata['chunk_index'] = idx
            chunk_metadata['chunk_count'] = len(chunks)
            chunk_metadata['chunk_size'] = len(chunk)
            
            result.append((chunk, chunk_metadata))
        
        return result


def chunk_documents(
    texts: List[str],
    similarity_threshold: float = 0.75,
    min_chunk_size: int = 80,
    max_chunk_size: int = 1200
) -> List[str]:
    """
    여러 텍스트를 배치로 청킹하는 헬퍼 함수
    
    Args:
        texts: 텍스트 리스트
        similarity_threshold: 유사도 임계값
        min_chunk_size: 최소 청크 크기
        max_chunk_size: 최대 청크 크기
        
    Returns:
        모든 청크의 리스트
    """
    chunker = SemanticChunker(
        similarity_threshold=similarity_threshold,
        min_chunk_size=min_chunk_size,
        max_chunk_size=max_chunk_size
    )
    
    all_chunks = []
    for text in texts:
        chunks = chunker.chunk_text(text)
        all_chunks.extend(chunks)
    
    return all_chunks


if __name__ == "__main__":
    # 테스트 코드
    print("=" * 60)
    print("SemanticChunker 테스트")
    print("=" * 60)
    
    test_text = """
    인공지능 기술이 빠르게 발전하고 있습니다. 특히 자연어 처리 분야에서 놀라운 성과를 보이고 있죠.
    GPT와 같은 대규모 언어 모델은 사람처럼 자연스러운 텍스트를 생성할 수 있습니다.
    
    한편 이미지 생성 AI도 큰 주목을 받고 있습니다. Stable Diffusion과 DALL-E 같은 모델들이 대표적이에요.
    이러한 AI 모델들은 예술 분야에도 영향을 미치고 있습니다.
    
    하지만 AI 윤리 문제도 중요합니다. 편향성과 프라이버시 보호가 핵심 이슈입니다.
    책임 있는 AI 개발을 위한 노력이 필요합니다.
    """
    
    chunker = SemanticChunker(similarity_threshold=0.7)
    chunks = chunker.chunk_text(test_text)
    
    print(f"\n총 {len(chunks)}개의 청크가 생성되었습니다:\n")
    for idx, chunk in enumerate(chunks, 1):
        print(f"[청크 {idx}] ({len(chunk)}자)")
        print(chunk)
        print("-" * 60)

