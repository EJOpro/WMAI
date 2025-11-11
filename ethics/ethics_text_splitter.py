"""
Ethics 텍스트 분할 모듈
kss(Korean Sentence Splitter)를 사용한 한국어 문장 분리
독립적으로 구현 (chrun_backend 참조 없음)
"""

import logging
from typing import List

# 로깅 설정
logger = logging.getLogger(__name__)


class EthicsTextSplitter:
    """
    kss를 사용하여 텍스트를 문장 단위로 분할하는 클래스
    """
    
    def __init__(self, min_sentence_length: int = 10):
        """
        Args:
            min_sentence_length (int): 최소 문장 길이 (기본값: 10자)
        """
        self.min_sentence_length = min_sentence_length
        self._kss_available = False
        
        # kss 라이브러리 import 시도
        try:
            import kss
            self._kss = kss
            self._kss_available = True
            logger.info("kss 라이브러리를 사용한 한국어 문장 분리기 활성화")
        except ImportError:
            logger.warning("kss 라이브러리가 설치되지 않았습니다. pip install kss 실행 필요. 폴백 모드로 동작합니다.")
            import re
            self._re = re
            self.sentence_pattern = re.compile(r'[.!?]+\s*(?=\s|$|\n)')
    
    def split_to_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분할합니다.
        
        Args:
            text (str): 분할할 원문 텍스트
            
        Returns:
            List[str]: 분할된 문장 리스트 (최소 길이 필터링 적용)
        """
        if not text or not text.strip():
            return []
        
        # kss 사용 가능 여부에 따라 분기
        if self._kss_available:
            sentences = self._split_with_kss(text)
        else:
            sentences = self._split_with_regex(text)
        
        # 최소 길이 필터링
        filtered_sentences = [
            sentence.strip() 
            for sentence in sentences 
            if len(sentence.strip()) >= self.min_sentence_length
        ]
        
        return filtered_sentences
    
    def _split_with_kss(self, text: str) -> List[str]:
        """
        kss를 사용한 한국어 문장 분할
        
        Args:
            text (str): 분할할 텍스트
            
        Returns:
            List[str]: 분할된 문장 리스트
        """
        try:
            # kss.split_sentences()는 한국어 문장 분리에 최적화됨
            # - 종결 어미 인식 (다, 요, 임 등)
            # - 따옴표, 괄호 처리
            # - 줄임표, 특수 문장부호 처리
            sentences = self._kss.split_sentences(text)
            
            logger.debug(f"kss로 {len(sentences)}개 문장 분할 완료")
            return sentences
            
        except Exception as e:
            logger.error(f"kss 문장 분할 중 오류 발생: {e}, 폴백 모드로 전환")
            return self._split_with_regex(text)
    
    def _split_with_regex(self, text: str) -> List[str]:
        """
        정규식을 사용한 폴백 문장 분할 (kss 사용 불가 시)
        
        Args:
            text (str): 분할할 텍스트
            
        Returns:
            List[str]: 분할된 문장 리스트
        """
        # 텍스트 전처리: 연속된 공백 제거, 줄바꿈 정리
        cleaned_text = self._re.sub(r'\s+', ' ', text.strip())
        
        # 정규표현식으로 문장 분할
        sentences = self.sentence_pattern.split(cleaned_text)
        
        # 빈 문자열 제거 및 공백 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 문장 부호가 제거된 경우를 위한 후처리
        processed_sentences = []
        for sentence in sentences:
            # 문장이 문장부호로 끝나지 않는 경우 마침표 추가
            if sentence and not sentence[-1] in '.!?':
                # 충분히 긴 문장인 경우만 마침표 추가
                if len(sentence) > 10:
                    sentence += '.'
            processed_sentences.append(sentence)
        
        logger.debug(f"정규식으로 {len(processed_sentences)}개 문장 분할 완료")
        return processed_sentences


# 편의를 위한 함수형 인터페이스
def split_to_sentences(text: str, min_length: int = 10) -> List[str]:
    """
    텍스트를 문장 단위로 분할하는 편의 함수
    
    Args:
        text (str): 분할할 원문 텍스트
        min_length (int): 최소 문장 길이 (기본값: 10자)
        
    Returns:
        List[str]: 분할된 문장 리스트
    """
    splitter = EthicsTextSplitter(min_sentence_length=min_length)
    return splitter.split_to_sentences(text)

