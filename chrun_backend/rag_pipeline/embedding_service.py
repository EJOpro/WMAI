"""
임베딩 서비스 모듈
문장을 벡터로 변환하여 유사도 검색에 사용할 수 있도록 하는 기능을 제공합니다.
"""

import os
import logging
from typing import List, Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 임베딩 모델 상수
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI 최신 임베딩 모델
EMBEDDING_DIMENSION = 1536  # text-embedding-3-small의 기본 차원

# 로깅 설정
logger = logging.getLogger(__name__)


def get_embedding(text: str) -> List[float]:
    """
    텍스트를 벡터 임베딩으로 변환하는 함수
    
    Args:
        text (str): 임베딩을 생성할 텍스트
        
    Returns:
        List[float]: 벡터 임베딩 (1536차원)
        
    환경변수 설정 예시:
        .env 파일에 다음과 같이 설정:
        OPENAI_API_KEY=sk-your-openai-api-key-here
        
    Note:
        - OpenAI API 키가 없으면 더미 벡터를 반환합니다
        - 실제 운영 환경에서는 반드시 유효한 API 키를 설정해야 합니다
    """
    
    # 입력 검증
    if not text or not text.strip():
        logger.warning("빈 텍스트가 입력되었습니다. 더미 벡터를 반환합니다.")
        return _get_dummy_embedding()
    
    # 환경변수에서 OpenAI API 키 읽기
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. 더미 벡터를 반환합니다.")
        logger.info("환경변수 설정 방법: .env 파일에 OPENAI_API_KEY=sk-your-key-here 추가")
        return _get_dummy_embedding()
    
    try:
        # OpenAI 클라이언트 import (지연 import로 의존성 문제 방지)
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
            encoding_format="float"  # float 형식으로 반환
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
        logger.info("오류로 인해 더미 벡터를 반환합니다.")
        
        # TODO: 오류 유형별 세부 처리
        # - API 키 오류: 401 Unauthorized
        # - 할당량 초과: 429 Too Many Requests  
        # - 네트워크 오류: ConnectionError
        # - 텍스트 길이 초과: 400 Bad Request
        
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
    
    Args:
        texts (List[str]): 임베딩을 생성할 텍스트 리스트
        
    Returns:
        List[List[float]]: 각 텍스트에 대한 임베딩 벡터 리스트
        
    TODO: 배치 처리 최적화
        - OpenAI API의 배치 요청 기능 활용
        - 토큰 제한 고려한 청크 분할
        - 병렬 처리로 성능 개선
    """
    
    if not texts:
        logger.warning("빈 텍스트 리스트가 입력되었습니다.")
        return []
    
    # 현재는 단순히 개별 호출로 처리 (추후 배치 API 적용 예정)
    embeddings = []
    
    for i, text in enumerate(texts):
        logger.debug(f"배치 임베딩 생성 중: {i+1}/{len(texts)}")
        embedding = get_embedding(text)
        embeddings.append(embedding)
    
    logger.info(f"배치 임베딩 생성 완료: {len(embeddings)}개 벡터")
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
    
    # 영벡터 검증 (모든 값이 0인 경우 더미 벡터로 간주)
    if all(x == 0.0 for x in embedding):
        logger.debug("더미 임베딩 벡터가 감지되었습니다.")
        # 더미 벡터도 유효한 것으로 처리 (fallback 용도)
    
    return True


# 환경변수 설정 가이드를 위한 함수
def check_environment() -> dict:
    """
    임베딩 서비스 환경 설정 상태를 확인하는 함수
    
    Returns:
        dict: 환경 설정 상태 정보
    """
    
    status = {
        "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": EMBEDDING_DIMENSION,
        "environment_file_exists": os.path.exists(".env")
    }
    
    # 설정 가이드 메시지
    if not status["openai_api_key_set"]:
        logger.info("=" * 50)
        logger.info("임베딩 서비스 설정 가이드")
        logger.info("=" * 50)
        logger.info("1. 프로젝트 루트에 .env 파일을 생성하세요")
        logger.info("2. .env 파일에 다음 내용을 추가하세요:")
        logger.info("   OPENAI_API_KEY=sk-your-openai-api-key-here")
        logger.info("3. OpenAI API 키는 https://platform.openai.com/api-keys 에서 발급받으세요")
        logger.info("=" * 50)
    
    return status


if __name__ == "__main__":
    # 테스트 실행
    print("임베딩 서비스 테스트 시작...")
    
    # 환경 확인
    env_status = check_environment()
    print(f"환경 설정 상태: {env_status}")
    
    # 테스트 문장
    test_sentence = "이 서비스는 정말 좋아요!"
    
    # 임베딩 생성 테스트
    embedding = get_embedding(test_sentence)
    print(f"테스트 문장: {test_sentence}")
    print(f"임베딩 차원: {len(embedding)}")
    print(f"임베딩 유효성: {validate_embedding(embedding)}")
    
    # 배치 테스트
    test_sentences = [
        "서비스가 마음에 들어요",
        "이용하기 어려워요",
        "도움이 많이 되었습니다"
    ]
    
    batch_embeddings = get_embeddings_batch(test_sentences)
    print(f"배치 임베딩 개수: {len(batch_embeddings)}")
    
    print("임베딩 서비스 테스트 완료!")
