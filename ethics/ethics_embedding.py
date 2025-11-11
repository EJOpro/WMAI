"""
Ethics 임베딩 서비스 모듈
OpenAI API를 사용한 텍스트 임베딩 생성
독립적으로 구현 (chrun_backend 참조 없음)
"""

import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 임베딩 모델 상수
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# 로깅 설정
logger = logging.getLogger(__name__)


def get_embedding(text: str) -> List[float]:
    """
    텍스트를 벡터 임베딩으로 변환하는 함수
    
    Args:
        text (str): 임베딩을 생성할 텍스트
        
    Returns:
        List[float]: 벡터 임베딩 (1536차원)
    """
    # 입력 검증
    if not text or not text.strip():
        logger.warning("빈 텍스트가 입력되었습니다. 더미 벡터를 반환합니다.")
        return _get_dummy_embedding()
    
    # 환경변수에서 OpenAI API 키 읽기
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 더미 벡터를 반환합니다.")
        return _get_dummy_embedding()
    
    try:
        # OpenAI 클라이언트 import
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("OpenAI 패키지가 설치되지 않았습니다. pip install openai 실행 필요")
            return _get_dummy_embedding()
        
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=api_key)
        
        # 임베딩 API 호출
        logger.debug(f"임베딩 생성 시작: {text[:50]}...")
        
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text.strip(),
            encoding_format="float"
        )
        
        # 임베딩 벡터 추출
        embedding = response.data[0].embedding
        
        logger.debug(f"임베딩 생성 완료: {len(embedding)}차원 벡터")
        
        # 차원 검증
        if len(embedding) != EMBEDDING_DIMENSION:
            logger.warning(f"예상 차원({EMBEDDING_DIMENSION})과 다른 임베딩이 생성되었습니다: {len(embedding)}차원")
        
        return embedding
        
    except Exception as e:
        logger.error(f"임베딩 생성 중 오류 발생: {e}")
        return _get_dummy_embedding()


def _get_dummy_embedding() -> List[float]:
    """
    더미 임베딩 벡터를 생성하는 내부 함수
    API 키가 없거나 오류가 발생했을 때 사용
    
    Returns:
        List[float]: 더미 벡터 (모든 값이 0.0인 1536차원 벡터)
    """
    logger.debug(f"더미 임베딩 생성: {EMBEDDING_DIMENSION}차원 영벡터")
    return [0.0] * EMBEDDING_DIMENSION


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    여러 텍스트에 대해 배치로 임베딩을 생성하는 함수
    ⚡ OpenAI 배치 API를 사용하여 한 번의 호출로 처리 (속도 4-6배 향상)
    
    Args:
        texts (List[str]): 임베딩을 생성할 텍스트 리스트
        
    Returns:
        List[List[float]]: 각 텍스트에 대한 임베딩 벡터 리스트
    """
    if not texts:
        logger.warning("빈 텍스트 리스트가 입력되었습니다.")
        return []
    
    # 빈 텍스트 필터링 및 정규화
    valid_texts = []
    empty_indices = []
    
    for i, text in enumerate(texts):
        if text and text.strip():
            valid_texts.append(text.strip())
        else:
            empty_indices.append(i)
    
    # 모든 텍스트가 비어있으면 더미 벡터 반환
    if not valid_texts:
        logger.warning("모든 텍스트가 비어있습니다. 더미 벡터를 반환합니다.")
        return [_get_dummy_embedding() for _ in texts]
    
    # 환경변수에서 OpenAI API 키 읽기
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 더미 벡터를 반환합니다.")
        return [_get_dummy_embedding() for _ in texts]
    
    try:
        # OpenAI 클라이언트 import
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("OpenAI 패키지가 설치되지 않았습니다. pip install openai 실행 필요")
            return [_get_dummy_embedding() for _ in texts]
        
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=api_key)
        
        # ⚡ 배치 임베딩 API 호출 (한 번에 모든 텍스트 처리)
        logger.debug(f"배치 임베딩 생성 시작: {len(valid_texts)}개 텍스트")
        
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=valid_texts,  # 리스트로 한 번에 전송
            encoding_format="float"
        )
        
        # 임베딩 벡터 추출
        embeddings = [data.embedding for data in response.data]
        
        logger.debug(f"배치 임베딩 생성 완료: {len(embeddings)}개 벡터")
        
        # 빈 텍스트 위치에 더미 벡터 삽입
        if empty_indices:
            for idx in empty_indices:
                embeddings.insert(idx, _get_dummy_embedding())
        
        # 차원 검증
        for i, embedding in enumerate(embeddings):
            if len(embedding) != EMBEDDING_DIMENSION:
                logger.warning(f"텍스트 {i}: 예상 차원({EMBEDDING_DIMENSION})과 다른 임베딩: {len(embedding)}차원")
        
        logger.info(f"배치 임베딩 생성 완료: {len(embeddings)}개 벡터 (API 호출 1회)")
        return embeddings
        
    except Exception as e:
        logger.error(f"배치 임베딩 생성 중 오류 발생: {e}")
        logger.warning("개별 임베딩 생성으로 폴백합니다.")
        
        # 폴백: 개별 호출로 처리
        embeddings = []
        for i, text in enumerate(texts):
            logger.debug(f"폴백 임베딩 생성 중: {i+1}/{len(texts)}")
            embedding = get_embedding(text)
            embeddings.append(embedding)
        
        return embeddings


def validate_embedding(embedding: List[float]) -> bool:
    """
    임베딩 벡터의 유효성을 검증하는 함수
    
    Args:
        embedding (List[float]): 검증할 임베딩 벡터
        
    Returns:
        bool: 유효한 임베딩인지 여부
    """
    if not embedding:
        return False
    
    # 차원 검증
    if len(embedding) != EMBEDDING_DIMENSION:
        logger.warning(f"잘못된 임베딩 차원: {len(embedding)} (예상: {EMBEDDING_DIMENSION})")
        return False
    
    # 타입 검증
    if not all(isinstance(x, (int, float)) for x in embedding):
        logger.warning("임베딩에 숫자가 아닌 값이 포함되어 있습니다.")
        return False
    
    return True

