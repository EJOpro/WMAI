"""
Ethics 텍스트 분할 모듈
문장 단위로 텍스트를 분할하는 기능 제공
독립적으로 구현 (chrun_backend 참조 없음)
"""

import re
from typing import List


class EthicsTextSplitter:
    """
    텍스트를 문장 단위로 분할하는 클래스
    """
    
    def __init__(self, min_sentence_length: int = 10):
        """
        Args:
            min_sentence_length (int): 최소 문장 길이 (기본값: 10자)
        """
        self.min_sentence_length = min_sentence_length
        # 한국어 문장 분할을 위한 정규표현식 패턴
        # 마침표, 물음표, 느낌표 뒤에 공백이나 줄바꿈이 오는 경우를 문장의 끝으로 판단
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
        
        # 텍스트 전처리: 연속된 공백 제거, 줄바꿈 정리
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        
        # 문장 분할
        sentences = self._split_sentences(cleaned_text)
        
        # 최소 길이 필터링
        filtered_sentences = [
            sentence.strip() 
            for sentence in sentences 
            if len(sentence.strip()) >= self.min_sentence_length
        ]
        
        return filtered_sentences
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        실제 문장 분할 로직
        
        Args:
            text (str): 분할할 텍스트
            
        Returns:
            List[str]: 분할된 문장 리스트
        """
        # 정규표현식으로 문장 분할
        sentences = self.sentence_pattern.split(text)
        
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

